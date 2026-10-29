-- 50% or more AI-generated
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- required for GiST equality used in exclusion constraints
CREATE EXTENSION IF NOT EXISTS "btree_gist";


CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- global platform feature flags
CREATE TABLE feature_flags (
    name VARCHAR(127) PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    rollout_percent INTEGER NOT NULL DEFAULT 0
        CONSTRAINT chk_feature_flags_rollout_percent CHECK (rollout_percent BETWEEN 0 AND 100),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_feature_flags_updated_at
BEFORE UPDATE ON feature_flags
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================================
-- global identities & organizations (tenants)
-- use the issuer + subject pair as the durable identity; email can change or collide.
CREATE TABLE identities (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    issuer TEXT NOT NULL,
    subject TEXT NOT NULL,
    email TEXT, -- informational attribute only; never used as an authorization id
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'deleted')),
    is_platform_operator BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    UNIQUE (issuer, subject)
);

CREATE TRIGGER trg_identities_updated_at
BEFORE UPDATE ON identities
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- every organization has an explicit owner, including during provisioning.
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    name TEXT NOT NULL,
    owner_identity_id UUID NOT NULL
        REFERENCES identities(id),
    status TEXT NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'suspended', 'deleted')),
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL))
);

CREATE INDEX idx_organizations_owner ON organizations (owner_identity_id);
CREATE TRIGGER trg_organizations_updated_at
BEFORE UPDATE ON organizations
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ============================================================================
-- tenant memberships & business personas
-- one identity can join many organizations, but only once per organization.
CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id),
    identity_id UUID NOT NULL
        REFERENCES identities(id),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'revoked')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    CONSTRAINT chk_memberships_revoked
        CHECK ((status = 'revoked') = (revoked_at IS NOT NULL)),
    UNIQUE (organization_id, id),
    UNIQUE (organization_id, identity_id)
);

CREATE INDEX idx_memberships_org_identity
    ON memberships (organization_id, identity_id, status);

CREATE TRIGGER trg_memberships_updated_at
BEFORE UPDATE ON memberships
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- profiles describe business personas, not authorization; permissions live separately
CREATE TABLE advisor_profiles (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    membership_id UUID NOT NULL,
    display_name TEXT,
    license_number TEXT,
    jurisdictions TEXT[] NOT NULL DEFAULT '{}',
    supervisory_membership_id UUID,
    timezone TEXT NOT NULL DEFAULT 'America/New_York',
    booking_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, membership_id),
    FOREIGN KEY (organization_id, membership_id)
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, supervisory_membership_id)
        REFERENCES memberships(organization_id, id)
);

CREATE TRIGGER trg_advisor_profiles_updated_at
BEFORE UPDATE ON advisor_profiles
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- composite foreign key prevents profiles from referencing another tenant's membership
CREATE TABLE staff_profiles (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    membership_id UUID NOT NULL,
    display_name TEXT,
    department TEXT,
    job_title TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, membership_id),
    FOREIGN KEY (organization_id, membership_id)
        REFERENCES memberships(organization_id, id)
);

CREATE TRIGGER trg_staff_profiles_updated_at
BEFORE UPDATE ON staff_profiles
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- subscriptions, primary resource containers & permission scopes

-- subscriptions partition tenant resources and provide a narrower permission boundary
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id),
    name TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT 'client_portfolio'
        CHECK (purpose IN ('default', 'client_portfolio', 'workspace')),
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'suspended', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    UNIQUE (organization_id, id)
);

CREATE TRIGGER trg_subscriptions_updated_at
BEFORE UPDATE ON subscriptions
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- guarantee at most one default subscription per organization
CREATE UNIQUE INDEX uq_one_default_subscription
    ON subscriptions (organization_id)
    WHERE is_default = TRUE AND status != 'deleted';

CREATE INDEX idx_subscriptions_org_status
    ON subscriptions (organization_id, status);

-- deferred constraint trigger to guarantee every active organization has a default subscription
CREATE OR REPLACE FUNCTION enforce_default_subscription_exists()
RETURNS TRIGGER AS $$
DECLARE
    v_org_id UUID;
BEGIN
    IF TG_TABLE_NAME = 'organizations' THEN
        v_org_id := NEW.id;
    ELSIF TG_OP = 'DELETE' THEN
        v_org_id := OLD.organization_id;
    ELSE
        v_org_id := NEW.organization_id;
    END IF;

    IF TG_TABLE_NAME = 'subscriptions' AND TG_OP = 'UPDATE' THEN
        IF OLD.organization_id IS DISTINCT FROM NEW.organization_id THEN
            IF EXISTS (
                SELECT 1
                FROM organizations o
                WHERE o.id = OLD.organization_id
                  AND o.status = 'active'
            )
            AND NOT EXISTS (
                SELECT 1
                FROM subscriptions s
                WHERE s.organization_id = OLD.organization_id
                  AND s.is_default = TRUE
                  AND s.status IN ('provisioning', 'active')
                  AND s.id IS DISTINCT FROM NEW.id
            ) THEN
                RAISE EXCEPTION
                    'Active organization % must have a usable default subscription',
                    OLD.organization_id
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END IF;

    -- affected organization must retain a usable default.
    IF EXISTS (
        SELECT 1
        FROM organizations o
        WHERE o.id = v_org_id
          AND o.status = 'active'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM subscriptions s
        WHERE s.organization_id = v_org_id
          AND s.is_default = TRUE
          AND s.status IN ('provisioning', 'active')
    ) THEN
        RAISE EXCEPTION
            'Active organization % must have a usable default subscription',
            v_org_id
            USING ERRCODE = '23514';
    END IF;

    -- Deferred AFTER triggers ignore the return value.
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_organization_default_subscription
AFTER INSERT OR UPDATE ON organizations
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION enforce_default_subscription_exists();

CREATE CONSTRAINT TRIGGER trg_subscription_default_invariant
AFTER INSERT OR UPDATE OR DELETE ON subscriptions
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION enforce_default_subscription_exists();

-- subscription-owned resources: clients, folders, documents, tasks, meetings

-- agents have a home subscription; cross-subscription work requires explicit delegation
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    home_subscription_id UUID NOT NULL,
    name TEXT NOT NULL,
    agent_type TEXT NOT NULL DEFAULT 'assistant',
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'deleted')),
    configuration_version INTEGER NOT NULL DEFAULT 1,
    max_delegation_ttl_seconds INTEGER NOT NULL DEFAULT 86400,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    created_by_membership_id UUID NOT NULL,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, created_by_membership_id) 
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, home_subscription_id)
        REFERENCES subscriptions(organization_id, id)
);

CREATE INDEX idx_agents_home_subscription
    ON agents (organization_id, home_subscription_id, status);

CREATE TRIGGER trg_agents_updated_at
BEFORE UPDATE ON agents
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- composite foreign keys enforce tenant and subscription ownership at database boundary
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    address TEXT,
    date_of_birth DATE,
    occupation TEXT,
    onboarding_stage TEXT
        CHECK (onboarding_stage IS NULL OR onboarding_stage IN (
            'corporate_introduction',
            'investment_education',
            'tax_education',
            'insurance_education',
            'financial_needs_analysis',
            'financial_plan'
        )),
    primary_advisor_membership_id UUID,
    status TEXT NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'archived', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    UNIQUE (organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, primary_advisor_membership_id)
        REFERENCES memberships(organization_id, id)
);

-- deduplicate active client emails within the same subscription
CREATE UNIQUE INDEX uq_clients_subscription_email
    ON clients (organization_id, subscription_id, lower(email))
    WHERE deleted_at IS NULL AND email IS NOT NULL;

-- optimized for listing active clients per subscription or advisor
CREATE INDEX idx_clients_subscription_active
    ON clients (organization_id, subscription_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_clients_advisor_active
    ON clients (organization_id, primary_advisor_membership_id)
    WHERE deleted_at IS NULL;

CREATE TRIGGER trg_clients_updated_at
BEFORE UPDATE ON clients
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE goals (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    client_id UUID NOT NULL,
    name TEXT NOT NULL,
    duration TEXT
        CHECK (duration IS NULL OR duration IN ('short_term', 'medium_term', 'long_term')),
    goal_type TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'achieved', 'archived', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    UNIQUE (organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, client_id)
        REFERENCES clients(organization_id, subscription_id, id)
);

CREATE INDEX idx_goals_client_active
    ON goals (organization_id, subscription_id, client_id)
    WHERE deleted_at IS NULL;

CREATE TRIGGER trg_goals_updated_at
BEFORE UPDATE ON goals
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    client_id UUID NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    -- when 'user', author_id = memberships.id; when 'agent', author_id = agents.id
    author_type TEXT NOT NULL
        CHECK (author_type IN ('user', 'agent')),
    author_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'archived', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    UNIQUE (organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, client_id)
        REFERENCES clients(organization_id, subscription_id, id)
);

CREATE INDEX idx_notes_client_chronological
    ON notes (organization_id, subscription_id, client_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE TRIGGER trg_notes_updated_at
BEFORE UPDATE ON notes
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- folder parents must belong to the same subscription; prevent only direct self-parenting
CREATE TABLE folders (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    parent_folder_id UUID,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    UNIQUE (organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, subscription_id, parent_folder_id)
        REFERENCES folders(organization_id, subscription_id, id),
    CHECK (parent_folder_id IS NULL OR parent_folder_id != id)
);

CREATE INDEX idx_folders_parent_active
    ON folders (organization_id, subscription_id, parent_folder_id)
    WHERE deleted_at IS NULL;

CREATE OR REPLACE FUNCTION enforce_folder_hierarchy_integrity()
RETURNS TRIGGER AS $$
DECLARE
    v_cycle_detected BOOLEAN;
BEGIN
    -- Never allow a folder to move across organizations or subscriptions
    IF NEW.organization_id IS DISTINCT FROM OLD.organization_id
       OR NEW.subscription_id IS DISTINCT FROM OLD.subscription_id
    THEN
        RAISE EXCEPTION 'Folder % cannot be moved across organizations or subscriptions', OLD.id
            USING ERRCODE = '23514';
    END IF;

    -- If moving to root (NULL) or parent_folder_id is unchanged, no cycle is possible
    IF NEW.parent_folder_id IS NULL
       OR NEW.parent_folder_id IS NOT DISTINCT FROM OLD.parent_folder_id
    THEN
        RETURN NEW;
    END IF;

    -- Walk up the ancestor chain from the new parent to ensure NEW.id is not an ancestor
    WITH RECURSIVE ancestors AS (
        SELECT id, parent_folder_id
        FROM folders
        WHERE organization_id = NEW.organization_id
          AND subscription_id = NEW.subscription_id
          AND id = NEW.parent_folder_id
        UNION ALL
        SELECT f.id, f.parent_folder_id
        FROM folders f
        INNER JOIN ancestors a
            ON f.organization_id = NEW.organization_id
           AND f.subscription_id = NEW.subscription_id
           AND f.id = a.parent_folder_id
    )
    SELECT EXISTS (
        SELECT 1 FROM ancestors WHERE id = NEW.id
    ) INTO v_cycle_detected;

    IF v_cycle_detected THEN
        RAISE EXCEPTION 'Cannot move folder % inside its own descendant %', NEW.id, NEW.parent_folder_id
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_folders_hierarchy_integrity
BEFORE UPDATE OF organization_id, subscription_id, parent_folder_id ON folders
FOR EACH ROW
EXECUTE FUNCTION enforce_folder_hierarchy_integrity();

-- documents can be associated with a client, a folder, both, or neither
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    folder_id UUID,
    client_id UUID,
    name TEXT NOT NULL,
    storage_key TEXT,
    classification TEXT NOT NULL DEFAULT 'confidential'
        CHECK (classification IN ('internal', 'confidential', 'restricted')),
    content_summary TEXT,
    workflow_status TEXT NOT NULL DEFAULT 'unsent'
        CHECK (workflow_status IN ('unsent', 'sent', 'yet_to_be_signed', 'signed', 'completed')),
    status TEXT NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'legal_hold', 'deleted')),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    UNIQUE (organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, subscription_id, folder_id)
        REFERENCES folders(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, client_id)
        REFERENCES clients(organization_id, subscription_id, id)
);

CREATE INDEX idx_documents_client_active
    ON documents (organization_id, subscription_id, client_id, created_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_documents_folder_active
    ON documents (organization_id, subscription_id, folder_id)
    WHERE deleted_at IS NULL;

CREATE TRIGGER trg_documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


CREATE TABLE meeting_types (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    advisor_membership_id UUID NOT NULL,
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL DEFAULT 30
        CHECK (duration_minutes BETWEEN 5 AND 480),
    slot_interval_minutes INTEGER NOT NULL DEFAULT 15
        CHECK (slot_interval_minutes IN (5, 10, 15, 20, 30, 60)),
    buffer_before_minutes INTEGER NOT NULL DEFAULT 0
        CHECK (buffer_before_minutes BETWEEN 0 AND 120),
    buffer_after_minutes INTEGER NOT NULL DEFAULT 0
        CHECK (buffer_after_minutes BETWEEN 0 AND 120),
    minimum_notice_minutes INTEGER NOT NULL DEFAULT 60
        CHECK (minimum_notice_minutes >= 0),
    max_days_in_advance INTEGER NOT NULL DEFAULT 60
        CHECK (max_days_in_advance BETWEEN 1 AND 365),
    meeting_mode TEXT NOT NULL DEFAULT 'video'
        CHECK (meeting_mode IN ('video', 'phone', 'in_person')),
    pre_meeting_agent_id UUID,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, subscription_id, id),
    UNIQUE (organization_id, advisor_membership_id, slug),
    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, advisor_membership_id)
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, pre_meeting_agent_id)
        REFERENCES agents(organization_id, id)
);

CREATE INDEX idx_meeting_types_advisor
    ON meeting_types (organization_id, subscription_id, advisor_membership_id)
    WHERE is_active = TRUE;

CREATE TRIGGER trg_meeting_types_updated_at
BEFORE UPDATE ON meeting_types
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- half-open ranges allow adjacent meetings without treating their shared boundary as overlap
-- GiST exclusion makes the no-overlapping-busy-meetings rule a database invariant
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    advisor_membership_id UUID,
    meeting_type_id UUID,
    folder_id UUID,
    client_id UUID,
    title TEXT NOT NULL,
    category TEXT,
    agenda TEXT,
    meeting_mode TEXT NOT NULL DEFAULT 'video'
        CHECK (meeting_mode IN ('video', 'phone', 'in_person')),
    location_or_platform TEXT,
    is_busy BOOLEAN NOT NULL DEFAULT TRUE,
    -- when 'user', organizer_id = memberships.id; when 'agent', organizer_id = agents.id
    organizer_type TEXT NOT NULL
        CHECK (organizer_type IN ('user', 'agent')),
    organizer_id UUID NOT NULL,
    attendee_membership_ids UUID[] NOT NULL DEFAULT '{}',
    scheduled_range TSTZRANGE NOT NULL
        CHECK (
            NOT isempty(scheduled_range)
            AND lower_inc(scheduled_range)
            AND NOT upper_inc(scheduled_range)
            AND (upper(scheduled_range) - lower(scheduled_range) <= INTERVAL '24 hours')
        ),
    scheduled_at TIMESTAMPTZ GENERATED ALWAYS AS (lower(scheduled_range)) STORED,
    duration_minutes INTEGER GENERATED ALWAYS AS (
        (EXTRACT(EPOCH FROM (upper(scheduled_range) - lower(scheduled_range))) / 60)::INTEGER
    ) STORED,
    status TEXT NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'cancelled', 'deleted')),
    completion_status TEXT NOT NULL DEFAULT 'scheduled'
        CHECK (completion_status IN ('scheduled', 'completed', 'no_show', 'rescheduled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    UNIQUE (organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, subscription_id, folder_id)
        REFERENCES folders(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, client_id)
        REFERENCES clients(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, advisor_membership_id)
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, subscription_id, meeting_type_id)
        REFERENCES meeting_types(organization_id, subscription_id, id),

    -- prevent an advisor from having two overlapping active busy meetings
    CONSTRAINT excl_meetings_no_advisor_busy_overlap
        EXCLUDE USING GIST (
            organization_id WITH =,
            advisor_membership_id WITH =,
            scheduled_range WITH &&
        )
        WHERE (status = 'active' AND is_busy = TRUE AND deleted_at IS NULL AND advisor_membership_id IS NOT NULL)
);

CREATE INDEX idx_meetings_client_active
    ON meetings (organization_id, subscription_id, client_id, scheduled_at DESC)
    WHERE deleted_at IS NULL;

CREATE TRIGGER trg_meetings_updated_at
BEFORE UPDATE ON meetings
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    advisor_membership_id UUID,
    folder_id UUID,
    client_id UUID,
    meeting_id UUID,
    title TEXT NOT NULL,
    description TEXT,
    tag TEXT,
    due_date DATE,
    -- when 'user', assignee_id = memberships.id; when 'agent', assignee_id = agents.id
    assignee_type TEXT
        CHECK (assignee_type IS NULL OR assignee_type IN ('user', 'agent')),
    assignee_id UUID,
    completed_at TIMESTAMPTZ
        CHECK ((task_status = 'completed') = (completed_at IS NOT NULL)),
    last_error TEXT,
    task_status TEXT NOT NULL DEFAULT 'todo'
        CHECK (task_status IN ('todo', 'in_progress', 'completed', 'cancelled', 'failed')),
    status TEXT NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'deleted')),
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_tasks_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    CONSTRAINT chk_tasks_completed_at
        CHECK ((task_status = 'completed') = (completed_at IS NOT NULL)),
    CONSTRAINT chk_tasks_assignee_pair
        CHECK (
            (assignee_type IS NULL AND assignee_id IS NULL)
            OR (assignee_type IS NOT NULL AND assignee_id IS NOT NULL)
        ),
    UNIQUE (organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, subscription_id, folder_id)
        REFERENCES folders(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, client_id)
        REFERENCES clients(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, meeting_id)
        REFERENCES meetings(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, advisor_membership_id)
        REFERENCES memberships(organization_id, id)
);

CREATE INDEX idx_tasks_assignee_active
    ON tasks (organization_id, assignee_type, assignee_id, task_status)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_tasks_client_active
    ON tasks (organization_id, subscription_id, client_id, task_status)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_advisor_due_active
    ON tasks (organization_id, advisor_membership_id, due_date ASC)
    WHERE deleted_at IS NULL AND task_status IN ('todo', 'in_progress');

CREATE TRIGGER trg_tasks_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


-- scheduling, availability, public booking engine

-- public booking links expose a booking flow, not direct access to private tenant resources
CREATE TABLE public_booking_links (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    organizer_membership_id UUID NOT NULL,
    advisor_membership_id UUID,
    meeting_type_id UUID,
    public_token TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    hold_ttl_seconds INTEGER NOT NULL DEFAULT 300
        CHECK (hold_ttl_seconds BETWEEN 60 AND 1800),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, organizer_membership_id) 
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, advisor_membership_id)
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, subscription_id, meeting_type_id)
        REFERENCES meeting_types(organization_id, subscription_id, id)
);

CREATE INDEX idx_public_booking_links_active_token
    ON public_booking_links (public_token)
    WHERE is_active = TRUE;

CREATE TRIGGER trg_public_booking_links_updated_at
BEFORE UPDATE ON public_booking_links
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- store recurring local business hours separately from dated exceptions
CREATE TABLE availability_rules (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    advisor_membership_id UUID NOT NULL,
    -- iso dow: 0 = sunday, 1 = monday, ..., 6 = saturday
    day_of_week SMALLINT NOT NULL
        CHECK (day_of_week BETWEEN 0 AND 6),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'America/New_York',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_until DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, advisor_membership_id)
        REFERENCES memberships(organization_id, id) ON DELETE CASCADE,
    CONSTRAINT chk_availability_rule_time_order
        CHECK (end_time > start_time),
    CONSTRAINT chk_availability_rule_validity_window
        CHECK (valid_until IS NULL OR valid_until >= valid_from)
);

CREATE INDEX idx_availability_rules_advisor_active
    ON availability_rules (organization_id, advisor_membership_id, day_of_week)
    WHERE is_active = TRUE;

CREATE TRIGGER trg_availability_rules_updated_at
BEFORE UPDATE ON availability_rules
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- overrides represent date-specific availability or closures that take precedence in scheduling
CREATE TABLE availability_overrides (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    advisor_membership_id UUID NOT NULL,
    override_date DATE NOT NULL,
    is_available BOOLEAN NOT NULL DEFAULT FALSE,
    custom_window TSTZRANGE,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, advisor_membership_id)
        REFERENCES memberships(organization_id, id) ON DELETE CASCADE,
    CONSTRAINT chk_override_window_bounds
        CHECK (
            custom_window IS NULL
            OR (
                NOT isempty(custom_window)
                AND lower_inc(custom_window)
                AND NOT upper_inc(custom_window)
                AND (upper(custom_window) - lower(custom_window) <= INTERVAL '24 hours')
            )
        ),
    CONSTRAINT chk_override_available_requires_window
        CHECK (
            (is_available = TRUE AND custom_window IS NOT NULL)
            OR (is_available = FALSE)
        )
);

CREATE INDEX idx_availability_overrides_advisor_date
    ON availability_overrides (organization_id, advisor_membership_id, override_date);

CREATE TRIGGER trg_availability_overrides_updated_at
BEFORE UPDATE ON availability_overrides
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE public_prospects (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    company_name TEXT,
    linked_client_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, subscription_id, linked_client_id)
        REFERENCES clients(organization_id, subscription_id, id)
);

CREATE UNIQUE INDEX uq_public_prospects_email
    ON public_prospects (organization_id, subscription_id, lower(email));

CREATE TRIGGER trg_public_prospects_updated_at
BEFORE UPDATE ON public_prospects
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- a hold temporarily reserves capacity; confirmation converts it into a durable booking
-- reserve buffers as well as the client-visible slot to prevent back-to-back meetings
-- from violating preparation, travel, or follow-up requirements.
-- exclusion constraint is the final database-level guard against overlapping reservations
CREATE TABLE bookings (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID NOT NULL,
    advisor_membership_id UUID NOT NULL,
    booking_link_id UUID NOT NULL,
    meeting_type_id UUID NOT NULL,
    prospect_id UUID,
    client_id UUID,
    internal_meeting_id UUID,
    status TEXT NOT NULL DEFAULT 'HELD'
        CHECK (status IN ('HELD', 'CONFIRMED', 'CANCELLED', 'EXPIRED')),
    -- client-visible appointment interval: [start_at, end_at)
    slot_range TSTZRANGE NOT NULL,
    -- conflict-enforced interval including buffers: [start_at - buffer_before, end_at + buffer_after)
    reserved_range TSTZRANGE NOT NULL,
    prospect_timezone TEXT NOT NULL DEFAULT 'UTC',
    meeting_topic TEXT,
    prospect_notes TEXT,
    hold_expires_at TIMESTAMPTZ,
    -- sha-256 hex digest of the high-entropy cancellation/management token
    cancel_token_hash TEXT UNIQUE,
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,
    rescheduled_from_id UUID,
    idempotency_key TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (organization_id, subscription_id, id),
    UNIQUE (organization_id, idempotency_key),

    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, advisor_membership_id)
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, subscription_id, booking_link_id)
        REFERENCES public_booking_links(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, meeting_type_id)
        REFERENCES meeting_types(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, prospect_id)
        REFERENCES public_prospects(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, client_id)
        REFERENCES clients(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, internal_meeting_id)
        REFERENCES meetings(organization_id, subscription_id, id),
    FOREIGN KEY (organization_id, subscription_id, rescheduled_from_id)
        REFERENCES bookings(organization_id, subscription_id, id),

    -- range sanity checks: canonical half-open [start, end), non-empty, < 24h, reserved contains slot
    CONSTRAINT chk_bookings_slot_range_valid CHECK (
        NOT isempty(slot_range)
        AND NOT lower_inf(slot_range)
        AND NOT upper_inf(slot_range)
        AND isfinite(lower(slot_range))
        AND isfinite(upper(slot_range))
        AND lower_inc(slot_range)
        AND NOT upper_inc(slot_range)
        AND upper(slot_range) > lower(slot_range)
        AND upper(slot_range) - lower(slot_range) <= INTERVAL '24 hours'
    ),
    CONSTRAINT chk_bookings_reserved_range_valid CHECK (
        NOT isempty(reserved_range)
        AND NOT lower_inf(reserved_range)
        AND NOT upper_inf(reserved_range)
        AND isfinite(lower(reserved_range))
        AND isfinite(upper(reserved_range))
        AND lower_inc(reserved_range)
        AND NOT upper_inc(reserved_range)
        AND upper(reserved_range) > lower(reserved_range)
        AND reserved_range @> slot_range
        AND upper(reserved_range) - lower(reserved_range) <= INTERVAL '24 hours'
    ),
    -- lifecycle invariants per status
    CONSTRAINT chk_bookings_status_invariants CHECK (
        (status = 'HELD' AND hold_expires_at IS NOT NULL)
        OR (status = 'CONFIRMED' AND hold_expires_at IS NULL AND (prospect_id IS NOT NULL OR client_id IS NOT NULL) AND cancel_token_hash IS NOT NULL)
        OR (status = 'CANCELLED' AND cancelled_at IS NOT NULL)
        OR (status = 'EXPIRED')
    ),

    -- concurrency guarantee: scoped gist exclusion constraint
    -- prevents any two held or confirmed bookings for the same advisor from overlapping reserved_range
    CONSTRAINT excl_bookings_no_advisor_overlap
        EXCLUDE USING GIST (
            organization_id WITH =,
            advisor_membership_id WITH =,
            reserved_range WITH &&
        )
        WHERE (status IN ('HELD', 'CONFIRMED'))
);

CREATE TRIGGER trg_bookings_updated_at
BEFORE UPDATE ON bookings
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();


CREATE OR REPLACE FUNCTION lock_advisor_schedule_keys(
    p_keys TEXT[]
)
RETURNS VOID AS $$
DECLARE
    v_lock_id BIGINT;
BEGIN
    FOR v_lock_id IN
        SELECT DISTINCT hashtextextended(k, 0)
        FROM unnest(p_keys) AS u(k)
        ORDER BY 1
    LOOP
        PERFORM pg_advisory_xact_lock(v_lock_id);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- expire stale holds during booking writes to reclaim capacity without relying solely on a worker
-- check internal meetings too: the booking exclusion constraint cannot see another table.
CREATE OR REPLACE FUNCTION enforce_booking_availability_and_evict_holds()
RETURNS TRIGGER AS $$
BEGIN
    -- serialize booking and meeting writes for the same advisor.
    IF TG_OP = 'UPDATE' THEN
        PERFORM lock_advisor_schedule_keys(ARRAY[
            OLD.organization_id::TEXT || ':' || OLD.advisor_membership_id::TEXT,
            NEW.organization_id::TEXT || ':' || NEW.advisor_membership_id::TEXT
        ]);
    ELSE
        PERFORM lock_advisor_schedule_keys(ARRAY[
            NEW.organization_id::TEXT || ':' || NEW.advisor_membership_id::TEXT
        ]);
    END IF;
    IF NEW.status IN ('HELD', 'CONFIRMED') THEN
        -- evict expired holds
        UPDATE bookings
        SET status = 'EXPIRED',
            updated_at = now(),
            version = version + 1
        WHERE organization_id = NEW.organization_id
          AND advisor_membership_id = NEW.advisor_membership_id
          AND status = 'HELD'
          AND hold_expires_at <= now()
          AND reserved_range && NEW.reserved_range
          AND id != NEW.id;

        -- prevent conflict against internal busy meetings (excluding the meeting linked to this booking)
        IF EXISTS (
            SELECT 1 FROM meetings m
            WHERE m.organization_id = NEW.organization_id
              AND m.advisor_membership_id = NEW.advisor_membership_id
              AND m.status = 'active'
              AND m.is_busy = TRUE
              AND m.deleted_at IS NULL
              AND m.scheduled_range && NEW.reserved_range
              AND (NEW.internal_meeting_id IS NULL OR m.id != NEW.internal_meeting_id)
        ) THEN
            RAISE EXCEPTION 'Advisor % has a conflicting busy internal meeting during %',
                NEW.advisor_membership_id, NEW.reserved_range
                USING ERRCODE = '23P01'; -- exclusion_violation
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Prevent recursive trigger execution when evicting expired booking holds:
DROP TRIGGER IF EXISTS trg_bookings_jit_evict_and_check_meetings ON bookings;
CREATE TRIGGER trg_bookings_jit_evict_and_check_meetings
BEFORE INSERT OR UPDATE OF
    organization_id, advisor_membership_id, subscription_id,
    meeting_type_id, slot_range, reserved_range, status,
    hold_expires_at, internal_meeting_id
ON bookings
FOR EACH ROW
WHEN (NEW.status IN ('HELD', 'CONFIRMED'))
EXECUTE FUNCTION enforce_booking_availability_and_evict_holds();

-- inverse check on `meetings` so inserting/updating a busy internal meeting cannot double-book over an active booking
CREATE OR REPLACE FUNCTION prevent_meeting_overlap_with_bookings()
RETURNS TRIGGER AS $$
BEGIN
    -- serialize schedule changes for the old and new advisor
    -- a null advisor has no schedule lock to acquire
    PERFORM lock_advisor_schedule_keys(
        array_remove(
            ARRAY[
                CASE
                    WHEN TG_OP = 'UPDATE'
                         AND OLD.advisor_membership_id IS NOT NULL
                    THEN OLD.organization_id::TEXT || ':' ||
                         OLD.advisor_membership_id::TEXT
                END,
                CASE
                    WHEN NEW.advisor_membership_id IS NOT NULL
                    THEN NEW.organization_id::TEXT || ':' ||
                         NEW.advisor_membership_id::TEXT
                END
            ],
            NULL
        )
    );

    IF NEW.status = 'active' 
        AND NEW.is_busy = TRUE 
        AND NEW.deleted_at IS NULL 
        AND NEW.advisor_membership_id IS NOT NULL 
    THEN
        IF EXISTS (
            SELECT 1 FROM bookings b
            WHERE b.organization_id = NEW.organization_id
              AND b.advisor_membership_id = NEW.advisor_membership_id
              AND (
                  b.status = 'CONFIRMED'
                  OR (b.status = 'HELD' AND b.hold_expires_at > now())
              )
              AND b.reserved_range && NEW.scheduled_range
              AND (b.internal_meeting_id IS NULL OR b.internal_meeting_id != NEW.id)
        ) THEN
            RAISE EXCEPTION 'Advisor % has an active booking overlapping meeting window %',
                NEW.advisor_membership_id, NEW.scheduled_range
                USING ERRCODE = '23P01'; -- exclusion_violation
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_meetings_check_booking_conflicts
BEFORE INSERT OR UPDATE OF scheduled_range, status, is_busy, deleted_at, advisor_membership_id ON meetings
FOR EACH ROW
EXECUTE FUNCTION prevent_meeting_overlap_with_bookings();


CREATE INDEX idx_bookings_advisor_start_time
    ON bookings (organization_id, advisor_membership_id, lower(slot_range))
    WHERE status IN ('HELD', 'CONFIRMED');

CREATE INDEX idx_bookings_expired_holds
    ON bookings (hold_expires_at)
    WHERE status = 'HELD';

CREATE INDEX idx_bookings_cancel_token_hash
    ON bookings (cancel_token_hash)
    WHERE status = 'CONFIRMED' AND cancel_token_hash IS NOT NULL;


-- groups are reusable principals; membership records support both people and agents
CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'deleted')),
    created_by_membership_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_clients_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    UNIQUE (organization_id, id),
    UNIQUE (organization_id, name),
    FOREIGN KEY (organization_id, created_by_membership_id)
        REFERENCES memberships(organization_id, id)
);

CREATE TRIGGER trg_groups_updated_at
BEFORE UPDATE ON groups
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE group_members (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    group_id UUID NOT NULL,
    membership_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'revoked')),
    added_by_membership_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    CONSTRAINT chk_group_memberships_revoked
        CHECK ((status = 'revoked') = (revoked_at IS NOT NULL)),
    FOREIGN KEY (organization_id, membership_id)
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, added_by_membership_id)
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, group_id)
        REFERENCES groups(organization_id, id)
);

CREATE UNIQUE INDEX uq_active_group_member
    ON group_members (organization_id, group_id, membership_id)
    WHERE status = 'active';


CREATE TABLE role_definitions (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id),
    name TEXT NOT NULL,
    description TEXT,
    resource_scope_type TEXT NOT NULL
        CHECK (resource_scope_type IN (
            'organization', 'subscription', 'client', 'goal',
            'note', 'folder', 'document', 'task', 'meeting'
        )),
    capabilities TEXT[] NOT NULL,
    is_system_role BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'deleted')),
    version INTEGER NOT NULL DEFAULT 1,
    created_by_membership_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT chk_role_definitions_soft_delete
        CHECK ((status = 'deleted') = (deleted_at IS NOT NULL)),
    CONSTRAINT chk_role_definitions_capabilities CHECK (
        cardinality(capabilities) > 0
        AND (
            -- Organization scope supports the 5 core capabilities + 4 org-admin capabilities
            (resource_scope_type = 'organization' AND capabilities <@ ARRAY[
                'view', 'create', 'edit', 'delete', 'propose', 'manage_access',
                'manage_subscriptions', 'manage_groups', 'manage_agents', 'manage_roles'
            ]::TEXT[])
            -- Container scopes support all 5 core capabilities (including 'create')
            OR (resource_scope_type IN ('subscription', 'client', 'folder', 'meeting') AND capabilities <@ ARRAY[
                'view', 'create', 'edit', 'delete', 'manage_access'
            ]::TEXT[])
            -- Leaf resource scopes only support view, edit, delete, manage_access
            OR (resource_scope_type IN ('goal', 'note', 'document', 'task') AND capabilities <@ ARRAY[
                'view', 'edit', 'delete', 'manage_access'
            ]::TEXT[])
        )
    ),
    -- Replaces UNIQUE (organization_id, id) and powers the scope-checked FK on role_assignments
    UNIQUE (organization_id, id, resource_scope_type),
    -- Allows standard role names ('viewer', 'editor', 'admin') per resource type in each org
    UNIQUE (organization_id, resource_scope_type, name),
    FOREIGN KEY (organization_id, created_by_membership_id)
        REFERENCES memberships(organization_id, id)
);

CREATE TRIGGER trg_role_definitions_updated_at
BEFORE UPDATE ON role_definitions
FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

CREATE TABLE role_assignments (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    subscription_id UUID,
    role_definition_id UUID NOT NULL,
    -- when 'user', subject_id = memberships.id; when 'group', groups.id; when 'agent', agents.id
    subject_type TEXT NOT NULL
        CHECK (subject_type IN ('user', 'group', 'agent')),
    subject_id UUID NOT NULL,
    scope_type TEXT NOT NULL
        CHECK (scope_type IN (
            'organization', 'subscription', 'client', 'goals',
            'note', 'folder', 'document', 'task', 'meeting'
        )),
    scope_id UUID NOT NULL,
    granted_by_membership_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'revoked', 'expired')),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT chk_role_assignments_revoked
        CHECK ((status = 'revoked') = (revoked_at IS NOT NULL)),
    -- Enforces that the role definition's resource_scope_type matches this assignment's scope_type
    FOREIGN KEY (organization_id, role_definition_id, scope_type)
        REFERENCES role_definitions(organization_id, id, resource_scope_type),
    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, granted_by_membership_id)
        REFERENCES memberships(organization_id, id),
    CONSTRAINT chk_role_assignments_subscription_scope
        CHECK (
            (scope_type = 'organization' AND subscription_id IS NULL AND scope_id = organization_id)
            OR (scope_type = 'subscription' AND subscription_id IS NOT NULL AND scope_id = subscription_id)
            OR (scope_type NOT IN ('organization', 'subscription') AND subscription_id IS NOT NULL)
        )
);

-- Prevents duplicate active assignments of the same role to the same principal on the same target
CREATE UNIQUE INDEX uq_role_assignments_active
    ON role_assignments (organization_id, subject_type, subject_id, scope_type, scope_id, role_definition_id)
    WHERE status IN ('provisioning', 'active');

-- Replaces idx_subscription_grants_lookup and idx_resource_grants_lookup
CREATE INDEX idx_role_assignments_target_lookup
    ON role_assignments (organization_id, subscription_id, scope_type, scope_id, status);

-- Replaces idx_subscription_grants_subject
CREATE INDEX idx_role_assignments_subject_lookup
    ON role_assignments (organization_id, subject_type, subject_id, status);


-- delegation is a bounded grant of agent authority, not an unrestricted identity impersonation
CREATE TABLE agent_delegations (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL,
    agent_id UUID NOT NULL,
    correlation_id TEXT,
    target_subscription_id UUID NOT NULL,
    target_resource_type TEXT
        CHECK (
            target_resource_type IS NULL
            OR target_resource_type IN (
                'client', 'goal', 'note', 'folder', 'document', 'task', 'meeting'
            )
        ),
    target_resource_id UUID,
    capabilities TEXT[] NOT NULL,
    permitted_tools TEXT[] NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'provisioning'
        CHECK (status IN ('provisioning', 'active', 'revoked', 'expired')),
    granted_by_membership_id UUID NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT chk_delegations_revoked
        CHECK ((status = 'revoked') = (revoked_at IS NOT NULL)),
    -- Strict governance: agents may only be delegated 'view' and 'propose'
    CONSTRAINT chk_agent_delegations_capabilities CHECK (
        cardinality(capabilities) > 0
        AND capabilities <@ ARRAY['view', 'propose']::TEXT[]
    ),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, granted_by_membership_id)
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, agent_id)
        REFERENCES agents(organization_id, id),
    FOREIGN KEY (organization_id, target_subscription_id)
        REFERENCES subscriptions(organization_id, id),
    CHECK (
        target_subscription_id IS NOT NULL
        AND (
            (target_resource_type IS NULL AND target_resource_id IS NULL)
            OR (target_resource_type IS NOT NULL AND target_resource_id IS NOT NULL)
        )
    )
);

CREATE INDEX idx_agent_delegations_active
    ON agent_delegations (organization_id, agent_id, expires_at)
    WHERE status = 'active';

-- human approval workflow for high-risk agent actions
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    organization_id UUID NOT NULL
        REFERENCES organizations(id),
    subscription_id UUID NOT NULL,
    requesting_agent_id UUID,
    requesting_membership_id UUID,
    delegation_id UUID,
    action_type TEXT NOT NULL,
    target_resource_type TEXT NOT NULL
        CHECK (target_resource_type IN (
            'client', 'goal', 'note', 'folder', 'document', 'task', 'meeting'
        )),
    target_resource_id UUID NOT NULL,
    action_payload JSONB NOT NULL,
    normalized_action_payload_hash TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    approver_membership_id UUID,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'executed')),
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    execution_result JSONB,
    UNIQUE (organization_id, idempotency_key),
    FOREIGN KEY (organization_id, requesting_membership_id)
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, approver_membership_id)
        REFERENCES memberships(organization_id, id),
    FOREIGN KEY (organization_id, subscription_id)
        REFERENCES subscriptions(organization_id, id),
    FOREIGN KEY (organization_id, requesting_agent_id)
        REFERENCES agents(organization_id, id),
    FOREIGN KEY (organization_id, delegation_id)
        REFERENCES agent_delegations(organization_id, id),
    
    -- Require at least one requester (agent or human membership)
    CONSTRAINT chk_approval_requests_requester_present CHECK (
        requesting_agent_id IS NOT NULL OR requesting_membership_id IS NOT NULL
    ),
    -- Prevent a human from approving their own request
    CONSTRAINT chk_approval_requests_no_self_approval CHECK (
        requesting_membership_id IS NULL
        OR approver_membership_id IS NULL
        OR requesting_membership_id != approver_membership_id
    ),
    -- Strict lifecycle invariants: 'approved' and 'executed' MUST have a human approver_membership_id
    CONSTRAINT chk_approval_requests_status_invariants CHECK (
        (status = 'pending' AND approver_membership_id IS NULL AND approved_at IS NULL AND executed_at IS NULL)
        OR (status = 'approved' AND approver_membership_id IS NOT NULL AND approved_at IS NOT NULL AND executed_at IS NULL)
        OR (status = 'executed' AND approver_membership_id IS NOT NULL AND approved_at IS NOT NULL AND executed_at IS NOT NULL)
        OR (status = 'rejected' AND approver_membership_id IS NOT NULL AND executed_at IS NULL)
        OR (status = 'expired' AND executed_at IS NULL)
    )
);

CREATE INDEX idx_approval_requests_pending
    ON approval_requests (organization_id, subscription_id, status, expires_at)
    WHERE status = 'pending';

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    -- nullable for platform events (global feature flag changes)
    organization_id UUID
        REFERENCES organizations(id),
    subscription_id UUID,
    actor_type TEXT NOT NULL
        CHECK (actor_type IN ('user', 'agent', 'platform', 'system')),
    actor_id TEXT NOT NULL,
    effective_subject_id TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    authorization_decision TEXT NOT NULL
        CHECK (authorization_decision IN ('allow', 'deny', 'not_applicable')),
    delegation_id UUID,
    correlation_id TEXT,
    request_id TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    outcome TEXT NOT NULL
        CHECK (outcome IN ('success', 'denied', 'error', 'pending_approval')),
    reason_code TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_audit_log_org_time
    ON audit_log (organization_id, occurred_at DESC);

CREATE INDEX idx_audit_log_platform_time
    ON audit_log (occurred_at DESC)
    WHERE organization_id IS NULL;

-- =============================================================================
-- thin tenant-isolation row-level security
-- =============================================================================
-- postgresql rls enforces a hard tenant boundary so a query missing a where
-- clause can never leak or mutate data across organizations.
--
-- usage in python middleware per request transaction:
--   set local app.current_org_id = '<uuid>';
--   or for background outbox/reaper workers: set local app.bypass_rls = 'on';

CREATE OR REPLACE FUNCTION current_tenant_org_id()
RETURNS UUID LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT NULLIF(current_setting('app.current_org_id', true), '')::UUID;
$$;

CREATE OR REPLACE FUNCTION is_rls_bypassed()
RETURNS BOOLEAN LANGUAGE sql STABLE PARALLEL SAFE AS $$
    SELECT current_setting('app.bypass_rls', true) = 'on';
$$;

DO $$
DECLARE
    t TEXT;
    tenant_tables TEXT[] := ARRAY[
        'memberships', 'advisor_profiles', 'staff_profiles', 'subscriptions',
        'agents', 'clients', 'goals', 'notes', 'folders',
        'documents', 'meetings', 'tasks', 'meeting_types',
        'public_booking_links', 'availability_rules', 'availability_overrides',
        'public_prospects', 'bookings', 'groups', 'group_members',
        'role_definitions', 'role_assignments', 'agent_delegations',
        'approval_requests'
    ];
BEGIN
    FOREACH t IN ARRAY tenant_tables LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', t);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY;', t);

        EXECUTE format($policy$
            CREATE POLICY tenant_isolation_fence ON %I
            FOR ALL
            USING (
                is_rls_bypassed()
                OR organization_id = current_tenant_org_id()
            )
            WITH CHECK (
                is_rls_bypassed()
                OR organization_id = current_tenant_org_id()
            );
        $policy$, t);
    END LOOP;
END;
$$;


ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE ROW LEVEL SECURITY;

-- Tenants can SELECT only their own org's logs; bypass sees all (including NULL org platform logs)
CREATE POLICY audit_log_select_policy ON audit_log
FOR SELECT
USING (
    is_rls_bypassed()
    OR (organization_id IS NOT NULL AND organization_id = current_tenant_org_id())
);

-- Tenants can INSERT logs for their own org; platform workers (with bypass) can insert NULL org logs
CREATE POLICY audit_log_insert_policy ON audit_log
FOR INSERT
WITH CHECK (
    is_rls_bypassed()
    OR (organization_id IS NOT NULL AND organization_id = current_tenant_org_id())
);
-- Because no FOR UPDATE or FOR DELETE policy exists, RLS denies all updates and deletes by default.

-- Defense-in-depth trigger: block UPDATE, DELETE, and TRUNCATE even when is_rls_bypassed() = true
CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only and immutable (% is prohibited)', TG_OP
        USING ERRCODE = '42501'; -- insufficient_privilege
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_immutable_row
BEFORE UPDATE OR DELETE ON audit_log
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_log_mutation();

CREATE TRIGGER trg_audit_log_immutable_stmt
BEFORE TRUNCATE ON audit_log
FOR EACH STATEMENT
EXECUTE FUNCTION prevent_audit_log_mutation();

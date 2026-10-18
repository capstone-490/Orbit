# Below 50% AI-generated

import argparse

from app.feature_flags import set_flag


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set a feature flag and record in audit log."
    )
    parser.add_argument("flag_name", type=str, help="Feature flag name")
    parser.add_argument(
        "enabled",
        type=str,
        choices=["true", "false"],
        help="Enable or disable the feature flag",
    )
    parser.add_argument("rollout_percent", type=int, help="Rollout percentage")
    parser.add_argument(
        "--description",
        type=str,
        default=None,
        help="Optional description for the feature flag",
    )
    parser.add_argument(
        "--changed_by", type=str, default=None, help="Who is making the change"
    )
    args = parser.parse_args()
    enabled = args.enabled == "true"

    set_flag(
        args.flag_name, enabled, args.rollout_percent, args.changed_by, args.description
    )
    print(
        f"Feature flag '{args.flag_name}' set to enabled = {enabled}, rollout_percent = {args.rollout_percent}, description ={args.description}, changed_by = {args.changed_by}"
    )

if __name__ == "__main__":
    main()

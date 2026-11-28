
// @vitest-environment jsdom
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import ClientNotes from '../components/client_profile/ClientNotes'
import {
  createClientNote,
  getClientNotes,
} from '../services/NotesApi'

vi.mock('../services/NotesApi', () => ({
  getClientNotes: vi.fn(),
  createClientNote: vi.fn(),
}))

const client = {
  id: 1,
  name: 'Alice Smith',
}

const existingNote = {
  id: 1,
  title: 'Investment discussion',
  content: 'Discussed investment goals.',
  client_id: 1,
  author_id: 1,
  author_type: 'Advisor',
  created_at: '2026-11-27T12:00:00Z',
  updated_at: '2026-11-27T12:00:00Z',
}

const newNote = {
  id: 2,
  title: 'Meeting preparation',
  content: 'Prepare questions for the next meeting.',
  client_id: 1,
  author_id: 1,
  author_type: 'Advisor',
  created_at: '2026-11-28T12:00:00Z',
  updated_at: '2026-11-28T12:00:00Z',
}

function renderNotes() {
  return render(
    <ClientNotes client={client} clientId={client.id} />,
  )
}

async function openAddNoteDialog() {
  await waitFor(() => {
    expect(
      screen.getByRole('button', { name: '+ Add Note' }),
    ).toBeEnabled()
  })

  fireEvent.click(
    screen.getByRole('button', { name: '+ Add Note' }),
  )

  return screen.getByRole('dialog')
}

function fillNoteForm(dialog, title, content) {
  fireEvent.change(
    within(dialog).getByLabelText('Title (optional)'),
    { target: { value: title } },
  )

  fireEvent.change(
    within(dialog).getByLabelText('Note content *'),
    { target: { value: content } },
  )
}


const dialogPrototype = window.HTMLDialogElement.prototype

const originalShowModal = Object.getOwnPropertyDescriptor(
  dialogPrototype,
  'showModal',
)

const originalClose = Object.getOwnPropertyDescriptor(
  dialogPrototype,
  'close',
)

beforeEach(() => {
  vi.resetAllMocks()

  getClientNotes.mockResolvedValue([])
  createClientNote.mockResolvedValue(newNote)

  Object.defineProperty(dialogPrototype, 'showModal', {
    configurable: true,
    writable: true,
    value: vi.fn(function () {
      this.setAttribute('open', '')
    }),
  })

  Object.defineProperty(dialogPrototype, 'close', {
    configurable: true,
    writable: true,
    value: vi.fn(function () {
      this.removeAttribute('open')
    }),
  })
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()

  if (originalShowModal) {
    Object.defineProperty(dialogPrototype, 'showModal', originalShowModal)
  } else {
    delete dialogPrototype.showModal
  }

  if (originalClose) {
    Object.defineProperty(dialogPrototype, 'close', originalClose)
  } else {
    delete dialogPrototype.close
  }
})


afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('ClientNotes', () => {
  it('displays the loading state', async () => {
    let resolveNotes

    getClientNotes.mockReturnValue(
      new Promise((resolve) => {
        resolveNotes = resolve
      }),
    )

    renderNotes()

    expect(screen.getByRole('status')).toHaveTextContent(
      'Loading client notes...',
    )

    expect(
      screen.getByRole('button', { name: '+ Add Note' }),
    ).toBeDisabled()

    await act(async () => {
      resolveNotes([])
    })

    expect(screen.getByText('No notes yet')).toBeInTheDocument()
  })

  it('loads and displays existing notes', async () => {
    getClientNotes.mockResolvedValue([existingNote])

    renderNotes()

    expect(
      await screen.findByText(existingNote.title),
    ).toBeInTheDocument()

    expect(
      screen.getByText(existingNote.content),
    ).toBeInTheDocument()

    expect(screen.getByText('Advisor note')).toBeInTheDocument()
    expect(screen.getByText('1 note · Newest first')).toBeInTheDocument()

    expect(getClientNotes).toHaveBeenCalledWith(1)
  })

  it('displays multiple notes in the returned order', async () => {
    getClientNotes.mockResolvedValue([newNote, existingNote])

    renderNotes()

    await screen.findByText(newNote.title)

    const cards = screen.getAllByRole('article')

    expect(cards).toHaveLength(2)
    expect(cards[0]).toHaveTextContent(newNote.title)
    expect(cards[1]).toHaveTextContent(existingNote.title)

    expect(
      screen.getByText('2 notes · Newest first'),
    ).toBeInTheDocument()
  })

  it('identifies AI-generated notes', async () => {
    getClientNotes.mockResolvedValue([
      {
        ...existingNote,
        author_type: 'Agent',
      },
    ])

    renderNotes()

    expect(
      await screen.findByText('AI-generated note'),
    ).toBeInTheDocument()
  })

  it('displays the empty state', async () => {
    renderNotes()

    expect(
      await screen.findByText('No notes yet'),
    ).toBeInTheDocument()

    expect(
      screen.getByRole('button', {
        name: '+ Add your first note',
      }),
    ).toBeInTheDocument()
  })

  it('opens the Add Note dialog', async () => {
    renderNotes()

    const dialog = await openAddNoteDialog()

    expect(dialog).toHaveAttribute('open')

    expect(dialog).toHaveTextContent(
      'Add an advisor note for Alice Smith.',
    )
  })

  it('opens the dialog from the empty state', async () => {
    renderNotes()

    const button = await screen.findByRole('button', {
      name: '+ Add your first note',
    })

    fireEvent.click(button)

    expect(screen.getByRole('dialog')).toHaveAttribute('open')
  })

  it('closes the dialog using Cancel', async () => {
    renderNotes()

    const dialog = await openAddNoteDialog()

    fireEvent.click(
      within(dialog).getByRole('button', { name: 'Cancel' }),
    )

    expect(dialog).not.toHaveAttribute('open')
  })

  it('closes the dialog using the close button', async () => {
    renderNotes()

    const dialog = await openAddNoteDialog()

    fireEvent.click(
      within(dialog).getByRole('button', {
        name: 'Close dialog',
      }),
    )

    expect(dialog).not.toHaveAttribute('open')
  })

  it('disables saving when content is empty', async () => {
    renderNotes()

    const dialog = await openAddNoteDialog()

    expect(
      within(dialog).getByRole('button', {
        name: 'Save Note',
      }),
    ).toBeDisabled()

    expect(createClientNote).not.toHaveBeenCalled()
  })

  it('disables saving when content contains only whitespace', async () => {
    renderNotes()

    const dialog = await openAddNoteDialog()

    fillNoteForm(dialog, 'Test note', '   ')

    expect(
      within(dialog).getByRole('button', {
        name: 'Save Note',
      }),
    ).toBeDisabled()

    expect(createClientNote).not.toHaveBeenCalled()
  })

  it('creates a note and displays it immediately', async () => {
    getClientNotes.mockResolvedValue([existingNote])

    renderNotes()

    const dialog = await openAddNoteDialog()

    fillNoteForm(dialog, newNote.title, newNote.content)

    fireEvent.click(
      within(dialog).getByRole('button', {
        name: 'Save Note',
      }),
    )

    expect(
      await screen.findByText(newNote.title),
    ).toBeInTheDocument()

    expect(createClientNote).toHaveBeenCalledWith(1, {
      title: newNote.title,
      content: newNote.content,
    })

    expect(dialog).not.toHaveAttribute('open')

    const cards = screen.getAllByRole('article')

    expect(cards).toHaveLength(2)
    expect(cards[0]).toHaveTextContent(newNote.title)
  })

  it('uses a default title when none is provided', async () => {
    createClientNote.mockResolvedValue({
      ...newNote,
      title: 'Advisor Note',
    })

    renderNotes()

    const dialog = await openAddNoteDialog()

    fillNoteForm(dialog, '', newNote.content)

    fireEvent.click(
      within(dialog).getByRole('button', {
        name: 'Save Note',
      }),
    )

    expect(
      await screen.findByRole('heading', {
        name: 'Advisor Note',
      }),
    ).toBeInTheDocument()

    expect(createClientNote).toHaveBeenCalledWith(1, {
      title: 'Advisor Note',
      content: newNote.content,
    })
  })

  it('trims whitespace before saving a note', async () => {
    renderNotes()

    const dialog = await openAddNoteDialog()

    fillNoteForm(
      dialog,
      `  ${newNote.title}  `,
      `  ${newNote.content}  `,
    )

    fireEvent.click(
      within(dialog).getByRole('button', {
        name: 'Save Note',
      }),
    )

    await screen.findByText(newNote.title)

    expect(createClientNote).toHaveBeenCalledWith(1, {
      title: newNote.title,
      content: newNote.content,
    })
  })

  it('displays an error when loading notes fails', async () => {
    getClientNotes.mockRejectedValue(
      new Error('Unable to load client notes.'),
    )

    renderNotes()

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent('Unable to load client notes.')

    expect(
      screen.getByRole('button', { name: '+ Add Note' }),
    ).toBeDisabled()
  })

  it('displays an error when saving a note fails', async () => {
    createClientNote.mockRejectedValue(
      new Error('Unable to create client note.'),
    )

    renderNotes()

    const dialog = await openAddNoteDialog()

    fillNoteForm(dialog, newNote.title, newNote.content)

    fireEvent.click(
      within(dialog).getByRole('button', {
        name: 'Save Note',
      }),
    )

    expect(
      await within(dialog).findByRole('alert'),
    ).toHaveTextContent('Unable to create client note.')

    expect(dialog).toHaveAttribute('open')

    expect(
      within(dialog).getByLabelText('Note content *'),
    ).toHaveValue(newNote.content)
  })

  it('disables form controls while saving', async () => {
    let resolveSave

    createClientNote.mockReturnValue(
      new Promise((resolve) => {
        resolveSave = resolve
      }),
    )

    renderNotes()

    const dialog = await openAddNoteDialog()

    fillNoteForm(dialog, newNote.title, newNote.content)

    fireEvent.click(
      within(dialog).getByRole('button', {
        name: 'Save Note',
      }),
    )

    expect(
      within(dialog).getByRole('button', {
        name: 'Saving...',
      }),
    ).toBeDisabled()

    expect(
      within(dialog).getByRole('button', { name: 'Cancel' }),
    ).toBeDisabled()

    expect(
      within(dialog).getByLabelText('Title (optional)'),
    ).toBeDisabled()

    expect(
      within(dialog).getByLabelText('Note content *'),
    ).toBeDisabled()

    await act(async () => {
      resolveSave(newNote)
    })

    expect(screen.getByText(newNote.title)).toBeInTheDocument()
    expect(dialog).not.toHaveAttribute('open')
  })

  it('updates the character count', async () => {
    renderNotes()

    const dialog = await openAddNoteDialog()

    fireEvent.change(
      within(dialog).getByLabelText('Note content *'),
      { target: { value: 'Hello' } },
    )

    expect(
      within(dialog).getByText('5/5000'),
    ).toBeInTheDocument()
  })

  it('resets the form when reopening the dialog', async () => {
    renderNotes()

    const dialog = await openAddNoteDialog()

    fillNoteForm(dialog, 'Unsaved title', 'Unsaved content')

    fireEvent.click(
      within(dialog).getByRole('button', { name: 'Cancel' }),
    )

    await openAddNoteDialog()

    expect(
      within(dialog).getByLabelText('Title (optional)'),
    ).toHaveValue('')

    expect(
      within(dialog).getByLabelText('Note content *'),
    ).toHaveValue('')
  })

  it('reloads notes when the selected client changes', async () => {
    getClientNotes.mockResolvedValueOnce([existingNote])

    const { rerender } = renderNotes()

    await screen.findByText(existingNote.title)

    getClientNotes.mockResolvedValueOnce([])

    rerender(
      <ClientNotes
        client={{ id: 2, name: 'Bob Jones' }}
        clientId={2}
      />,
    )

    expect(
      await screen.findByText('No notes yet'),
    ).toBeInTheDocument()

    expect(getClientNotes).toHaveBeenLastCalledWith(2)

    expect(
      screen.queryByText(existingNote.title),
    ).not.toBeInTheDocument()
  })
})

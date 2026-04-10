import { getInitData } from './telegram'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const initData = getInitData()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': initData,
      ...(options.headers ?? {}),
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Member {
  user_id: number
  intro_name: string | null
  intro_location: string | null
  intro_description: string | null
  intro_linkedin: string | null
  intro_hobbies_drivers: string | null
  intro_skills: string | null
  field_of_activity: string | null
  intro_birthday: string | null
  intro_image: string | null
  user_telegram_link: string | null
  thanks_received: number
  meetings_completed: number
  offer: string | null
  request_text: string | null
}

export interface Meeting {
  id: number
  user_1_id: number
  user_2_id: number
  status: string
  matched_user: Member
  created_at: string
}

export interface UpdateProfilePayload {
  intro_name?: string
  intro_location?: string
  intro_description?: string
  intro_linkedin?: string
  intro_hobbies_drivers?: string
  intro_skills?: string
  field_of_activity?: string
  offer?: string
  request_text?: string
}

// ─── Endpoints ────────────────────────────────────────────────────────────────

export const api = {
  // My profile
  getMe: () => request<Member>('/tma/me'),
  updateMe: (data: UpdateProfilePayload) =>
    request<Member>('/tma/me', { method: 'PUT', body: JSON.stringify(data) }),

  // Member directory
  getMembers: (search?: string) => {
    const q = search ? `?search=${encodeURIComponent(search)}` : ''
    return request<Member[]>(`/tma/members${q}`)
  },
  getMember: (userId: number) => request<Member>(`/tma/members/${userId}`),

  // Photo proxy (returns URL)
  photoUrl: (userId: number) => `${API_BASE}/tma/photo/${userId}`,

  // Match / meeting
  getPendingMatch: () => request<Meeting | null>('/tma/matches/pending'),
  findMatch: () => request<Meeting | null>('/tma/matches/find', { method: 'POST' }),
  getMeeting: (meetingId: number) => request<Meeting>(`/tma/meetings/${meetingId}`),
  confirmMeeting: (meetingId: number) =>
    request<void>(`/tma/meetings/${meetingId}/confirm`, { method: 'POST' }),
  declineMeeting: (meetingId: number) =>
    request<void>(`/tma/meetings/${meetingId}/decline`, { method: 'POST' }),
  alreadyKnow: (meetingId: number) =>
    request<void>(`/tma/meetings/${meetingId}/already_know`, { method: 'POST' }),
}

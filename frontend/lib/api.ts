const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || ""

interface ApiError {
  type: string
  title: string
  status: number
  detail: string
}

interface CalendarEventRequest {
  event_date: string  // YYYY-MM-DD
}

interface CalendarEventResponse {
  success: boolean
  message: string
  result: any
  event_summary: {
    title: string
    date: string
    time: string
  }
}

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`

    const response = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    })

    if (!response.ok) {
      const error: ApiError = await response.json()
      throw new Error(error.detail || "API 요청이 실패했습니다.")
    }

    return response.json()
  }

  async addToCalendar(
    request: CalendarEventRequest
  ): Promise<CalendarEventResponse> {
    return this.request<CalendarEventResponse>(
      `/add-to-calendar`,
      {
        method: "POST",
        body: JSON.stringify(request),
      }
    )
  }

  async register(username: string, password: string, interest: string, level: string) {
    return this.request<{
      user_id: number
      username: string
      interest: string
      level: string
      created_at: string
    }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, interest, level }),
    })
  }

  async login(username: string, password: string) {
    return this.request<{
      user_id: number
      username: string
      interest: string
      level: string
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    })
  }

  async getAdvice(userId: number) {
    return this.request<{
      advice_type: "interest_change" | "level_change" | "none"
      current_interest?: string
      suggested_interest?: string
      current_level?: string
      suggested_level?: string
      reason?: string
      message?: string
      comprehension_score?: number
    }>(`/${userId}/advice`)
  }

  async acceptInterestChange(userId: number, newInterest: string) {
    return this.request<{
      user_id: number
      updated_interest: string
      message: string
    }>(`/${userId}/advice/accept-interest`, {
      method: "POST",
      body: JSON.stringify({ new_interest: newInterest }),
    })
  }

  async acceptLevelChange(userId: number, newLevel: string) {
    return this.request<{
      user_id: number
      updated_level: string
      message: string
    }>(`/${userId}/advice/accept-level`, {
      method: "POST",
      body: JSON.stringify({ new_level: newLevel }),
    })
  }

  async getTodayRecommendations(userId: number) {
    return this.request<{
      date: string
      papers: Array<{
        paper_id: number
        title: string
        authors: string[]
        recommended_at: string
        is_user_requested: boolean
      }>
      total_count: number
    }>(`/${userId}/recommendations/today`)
  }
  
  async getTodayRecommendationsRelations(userId: number) {
  return this.request<{
    date: string
    graph: {
      nodes: Array<{
        id: number
        title: string
        type: "recommended" | "common_reference"
      }>
      edges: Array<{
        source: number
        target: number
        type: "cites"
        is_influential: boolean
      }>
    }
    analysis: {
      common_references: Array<{
        paper_id: number
        title: string
        cited_by_count: number
        suggestion: string
      }>
      clusters: Array<{
        theme: string
        papers: number[]
      }>
    }
  }>(`/${userId}/recommendations/today/relations1`)
}

  async requestPaper(userId: number, paperId: number, reason: string) {
    return this.request<{
      message: string
      paper_id: number
      title: string
      scheduled_date: string
    }>(`/${userId}/recommendations/request-paper1`, {
      method: "POST",
      body: JSON.stringify({ paper_id: paperId, reason }),
    })
  }

  async getPapersHistory(userId: number) {
    return this.request<{
      papers: Array<{
        paper_id: number
        title: string
        authors: string[]
        recommended_at: string
        is_user_requested: boolean
      }>
      total_count: number
    }>(`/${userId}/papers/history`)
  }

  async getPaperDetail(paperId: number, userId: number) {
    return this.request<{
      paper_id: number
      title: string
      authors: string[]
      published_date: string
      source: string
      arxiv_id: string
      pdf_url: string
      abstract: string
      summary: {
        level: string
        content: string
      }
      metadata: {
        citation_count: number
        citation_velocity: number
        influential_citation_count: number
        keywords: string[]
      }
      chat_history: Array<{
        chat_id: number
        question: string
        answer: string
        created_at: string
      }>
    }>(`/papers/${paperId}/${userId}`)
  }

  async updateProfile(userId: number, data: { interest: string; level: string }) {
    return this.request<{
      message: string
      user: {
        user_id: number
        username: string
        interest: string
        level: string
      }
    }>(`/users/${userId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    })
  }

  async sharePaperToKakao(paperId: number, paperTitle: string, pdfUrl: string | null, aiSummary: string | null) {
    return this.request<{
      success: boolean
      message: string
      result: any
    }>(`/papers/${paperId}/share-kakao`, {
      method: "POST",
      body: JSON.stringify({ 
        paper_title: paperTitle,
        pdf_url: pdfUrl,
        ai_summary: aiSummary
      }),
    })
  }

  async addPaperByArxivId(arxivId: string, userId: number) {
    return this.request<{
      message: string
    }>("/papers/add", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"  // ✅ 추가
      },
      body: JSON.stringify({
        arxiv_id: arxivId,
        user_id: 3
      })
    })
  }


  async chatWithPaper(paperId: number, userId: number, question: string) {
    return this.request<{
      chat_id: number
      paper_id: number
      question: string
      answer: string
      created_at: string
      context_used: {
        previous_chats: Array<{
          question: string
          answer: string
        }>
      }
    }>(`/papers/${paperId}/chat`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId, question }),
    })
  }
}




export const api = new ApiClient()

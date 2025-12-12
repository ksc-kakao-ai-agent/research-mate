"use client"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { api } from "@/lib/api"
import { NavigationHeader } from "@/components/navigation-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ArrowLeft, MessageSquare, Calendar, Sparkles, ExternalLink } from "lucide-react"

export default function PaperDetailPage() {
  const { user } = useAuth()
  const router = useRouter()
  const params = useParams()
  const paperId = Number.parseInt(params.id as string)

  const [paper, setPaper] = useState<{
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
  } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      router.push("/login")
    } else {
      fetchPaperDetail()
    }
  }, [user, router, paperId])

  const fetchPaperDetail = async () => {
    if (!user) return

    setIsLoading(true)
    setError(null)

    try {
      const data = await api.getPaperDetail(paperId, user.id)
      setPaper(data)
    } catch (error) {
      console.error("Failed to fetch paper detail:", error)
      setError("논문 정보를 불러오는데 실패했습니다.")
    } finally {
      setIsLoading(false)
    }
  }

  if (!user) {
    return null
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <NavigationHeader />
        <main className="container mx-auto px-4 py-8 max-w-5xl">
          <div className="text-center py-12">
            <p className="text-muted-foreground">논문 정보를 불러오는 중...</p>
          </div>
        </main>
      </div>
    )
  }

  if (error || !paper) {
    return (
      <div className="min-h-screen bg-background">
        <NavigationHeader />
        <main className="container mx-auto px-4 py-8 max-w-5xl">
          <div className="text-center py-12">
            <p className="text-destructive">{error || "논문을 찾을 수 없습니다."}</p>
            <Button className="mt-4" onClick={() => router.back()}>
              돌아가기
            </Button>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <NavigationHeader />

      <main className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="flex items-center justify-between mb-6">
          <Button variant="ghost" onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            뒤로 가기
          </Button>

          <Button onClick={() => router.push(`/paper/${paperId}/chat`)} size="lg">
            <MessageSquare className="h-4 w-4 mr-2" />이 논문에 대해 챗봇에게 질문하기
          </Button>
        </div>

        {/* Paper Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-4 flex-wrap">

            {/* 🔥 keywords가 null/undefined일 때 오류 안 나게 처리 */}
            {paper.metadata?.keywords?.length > 0 &&
              paper.metadata.keywords.map((keyword) => (
                <Badge key={keyword} variant="secondary" className="text-sm">
                  {keyword}
                </Badge>
              ))
            }

            {paper.summary?.level && (
              <Badge variant="outline" className="text-sm">
                {paper.summary.level === "beginner"
                  ? "초급"
                  : paper.summary.level === "intermediate"
                  ? "중급"
                  : "고급"}
              </Badge>
            )}


            <span className="text-sm text-muted-foreground flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              {new Date(paper.published_date).toLocaleDateString("ko-KR")}
            </span>
          </div>

          <h1 className="text-4xl font-bold mb-4 text-balance leading-tight">
            {paper.title}
          </h1>

          <div className="flex items-center gap-4 text-sm text-muted-foreground mb-4">
            <span>{paper.authors.join(", ")}</span>
            <span>•</span>
            <span>{paper.source}</span>

            {paper.arxiv_id && (
              <>
                <span>•</span>
                <span>{paper.arxiv_id}</span>
              </>
            )}
          </div>

          {paper.pdf_url && (
            <Button variant="outline" asChild>
              <a href={paper.pdf_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="h-4 w-4 mr-2" />
                PDF 다운로드
              </a>
            </Button>
          )}
        </div>


        <div className="space-y-6">
          {/* Metadata */}
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl">논문 정보</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">인용 수</p>
                  <p className="text-2xl font-bold">{paper.metadata.citation_count}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">영향력 있는 인용</p>
                  <p className="text-2xl font-bold">{paper.metadata.influential_citation_count}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-1">인용 속도</p>
                  <p className="text-2xl font-bold">{paper.metadata.citation_velocity}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Abstract */}
          <Card>
            <CardHeader>
              <CardTitle className="text-2xl">초록 (Abstract)</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-base leading-relaxed text-muted-foreground">{paper.abstract}</p>
            </CardContent>
          </Card>

          {/* AI Explanation */}
          <Card className="border-primary/30 bg-gradient-to-br from-primary/5 to-secondary/5">
            <CardHeader>
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                <CardTitle className="text-2xl">AI가 설명하는 이 논문</CardTitle>
              </div>
              <CardDescription>쉽게 이해할 수 있도록 AI가 요약했습니다</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-base leading-relaxed">{paper.summary?.content || "요약 정보가 제공되지 않았습니다."}</p>
            </CardContent>
          </Card>

          {/* Chat History */}
          {paper.chat_history.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-2xl flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" />
                  챗봇과 나눈 대화
                </CardTitle>
                <CardDescription>이 논문에 대해 나눈 질문과 답변입니다</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {paper.chat_history.map((chat, index) => (
                  <div key={chat.chat_id}>
                    <div className="flex justify-end mb-2">
                      <div className="bg-primary text-primary-foreground rounded-lg px-4 py-3 max-w-[80%]">
                        <p className="text-sm font-medium mb-1">나</p>
                        <p className="text-sm leading-relaxed">{chat.question}</p>
                      </div>
                    </div>
                    <div className="flex justify-start mb-2">
                      <div className="bg-muted rounded-lg px-4 py-3 max-w-[80%]">
                        <p className="text-sm font-medium mb-1">AI 챗봇</p>
                        <p className="text-sm leading-relaxed">{chat.answer}</p>
                      </div>
                    </div>
                    {index < paper.chat_history.length - 1 && <Separator className="my-4" />}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  )
}

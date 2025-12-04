"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { api } from "@/lib/api"
import { NavigationHeader } from "@/components/navigation-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Calendar } from "lucide-react"
import { PaperGraph } from "@/components/paper-graph"

export default function RecommendationsPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [papers, setPapers] = useState<
    Array<{
      paper_id: number
      title: string
      authors: string[]
      recommended_at: string
    }>
  >([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      router.push("/login")
    } else {
      fetchRecommendations()
    }
  }, [user, router])

  const fetchRecommendations = async () => {
    if (!user) return

    setIsLoading(true)
    setError(null)

    try {
      const data = await api.getTodayRecommendations(user.id)
      setPapers(data.papers.slice(0, 3))
    } catch (error) {
      console.error("Failed to fetch recommendations:", error)
      setError("추천 논문을 불러오는데 실패했습니다.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleRequestPaper = async () => {
    if (!user) return

    try {
      await api.requestPaper(user.id, 50, "common_reference")
      alert("내일 논문 추천 목록에 추가되었습니다.")
    } catch (error) {
      console.error("Failed to request paper:", error)
      alert("논문 요청에 실패했습니다.")
    }
  }

  if (!user) {
    return null
  }

  const todayPapers = papers.slice(0, 3)

  return (
    <div className="min-h-screen bg-background">
      <NavigationHeader />

      <main className="container mx-auto px-4 py-8 max-w-5xl">
        <Button variant="ghost" className="mb-6" onClick={() => router.push("/")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          홈으로 돌아가기
        </Button>

        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">오늘의 추천 논문</h1>
          <p className="text-muted-foreground">당신의 관심사에 맞춰 선별한 3편의 논문입니다</p>
        </div>

        {isLoading && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">논문을 불러오는 중...</p>
          </div>
        )}

        {error && (
          <div className="text-center py-12">
            <p className="text-destructive">{error}</p>
          </div>
        )}

        {!isLoading && !error && (
          <>
            <div className="space-y-4 mb-12">
              {todayPapers.map((paper, index) => (
                <Card
                  key={paper.paper_id}
                  className="cursor-pointer transition-all hover:shadow-lg hover:border-primary/50"
                  onClick={() => router.push(`/paper/${paper.paper_id}`)}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="secondary">{user.interest}</Badge>
                          <Badge variant="outline">
                            {user.level === "beginner" ? "초급" : user.level === "intermediate" ? "중급" : "고급"}
                          </Badge>
                        </div>
                        <CardTitle className="text-xl mb-2 text-balance">{paper.title}</CardTitle>
                        <CardDescription className="flex items-center gap-2 text-sm">
                          <Calendar className="h-4 w-4" />
                          {new Date(paper.recommended_at).toLocaleDateString("ko-KR")}
                        </CardDescription>
                        <CardDescription className="text-sm mt-2">{paper.authors.join(", ")}</CardDescription>
                      </div>
                      <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 text-primary font-bold text-xl">
                        {index + 1}
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              ))}
            </div>

            <Card className="bg-gradient-to-br from-accent/5 to-secondary/5">
              <CardHeader>
                <CardTitle className="text-2xl">논문 관계 분석</CardTitle>
                <CardDescription className="text-base">오늘 추천된 논문들 간의 연관성을 확인하세요</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="p-4 bg-card rounded-lg border border-border">
                  <p className="text-sm leading-relaxed mb-4">
                    논문 A와 B가 공통으로 인용하는 논문 D가 있네요. 내일은 D를 추천해드릴까요?
                  </p>
                  <PaperGraph />
                </div>
                <Button className="w-full" size="lg" onClick={handleRequestPaper}>
                  내일 해당 논문 추천받기
                </Button>
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  )
}

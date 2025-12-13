"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { api } from "@/lib/api"
import { NavigationHeader } from "@/components/navigation-header"
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Calendar } from "lucide-react"
import { cn } from "@/lib/utils"



interface PaperItem {
  paper_id: number
  title: string
  authors: string[]
  recommended_at: string
  is_user_requested: boolean // ✅ 추가된 필드
}


export default function HistoryPage() {
  const { user } = useAuth()
  const router = useRouter()
  const [papers, setPapers] = useState<PaperItem[]>([]) // 타입을 PaperItem[]으로 변경
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      router.push("/login")
    } else {
      fetchHistory()
    }
  }, [user, router])

  const fetchHistory = async () => {
    if (!user) return

    setIsLoading(true)
    setError(null)

    try {
      const data = await api.getPapersHistory(user.id)
      setPapers(data.papers)
    } catch (error) {
      console.error("Failed to fetch history:", error)
      setError("논문 이력을 불러오는데 실패했습니다.")
    } finally {
      setIsLoading(false)
    }
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-background">
      <NavigationHeader />

      <main className="container mx-auto px-4 py-8 max-w-5xl">
        <Button variant="ghost" className="mb-6" onClick={() => router.push("/")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          홈으로 돌아가기
        </Button>

        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">지금까지 공부한 논문</h1>
          <p className="text-muted-foreground">학습한 논문 목록과 복습이 필요한 논문을 확인하세요</p>
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

        {!isLoading && !error && papers.length === 0 && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">아직 학습한 논문이 없습니다.</p>
          </div>
        )}

        {!isLoading && !error && papers.length > 0 && (
          <div className="space-y-4">
            {papers.map((paper) => (
              <Card
                key={paper.paper_id}
                // 2. is_user_requested에 따라 스타일을 조건부로 변경합니다.
                className={cn(
                  "cursor-pointer transition-all hover:shadow-lg hover:border-primary/50 group",
                  paper.is_user_requested && "bg-amber-50/50 border-amber-300 ring-4 ring-amber-200/50" // 요청된 논문 강조
                )}
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
                        {paper.is_user_requested && ( // 3. 사용자 요청 논문 뱃지 추가
                          <Badge variant="default" className="bg-amber-500 hover:bg-amber-600">
                            ✍️ 직접 요청했어요
                          </Badge>
                        )}
                      </div>
                      <CardTitle className="text-xl mb-2 text-balance group-hover:text-primary transition-colors">
                        {paper.title}
                      </CardTitle>
                      <CardDescription className="flex items-center gap-4 text-sm">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-4 w-4" />
                          {new Date(paper.recommended_at).toLocaleDateString("ko-KR")}
                        </span>
                      </CardDescription>
                      <CardDescription className="text-sm mt-2">{paper.authors.join(", ")}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

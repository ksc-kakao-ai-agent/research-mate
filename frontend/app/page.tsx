"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { api } from "@/lib/api"
import { NavigationHeader } from "@/components/navigation-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { BookOpen, History, Lightbulb } from "lucide-react"

export default function HomePage() {
  const { user, updateInterest, updateLevel } = useAuth()
  const router = useRouter()
  const [advice, setAdvice] = useState<{
    advice_type: "interest_change" | "level_change" | "none"
    current_interest?: string
    suggested_interest?: string
    current_level?: string
    suggested_level?: string
    reason?: string
    message?: string
  } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      router.push("/login")
    } else {
      fetchAdvice()
    }
  }, [user, router])

  const fetchAdvice = async () => {
    if (!user) return

    setIsLoading(true)
    setError(null)

    try {
      const adviceData = await api.getAdvice(user.id)
      setAdvice(adviceData)
    } catch (error) {
      console.error("Failed to fetch advice:", error)
      setError("조언을 불러오는데 실패했습니다.")
    } finally {
      setIsLoading(false)
    }
  }

  if (!user) {
    return null
  }

  const handleChangeInterest = async () => {
    if (!advice || advice.advice_type !== "interest_change" || !advice.suggested_interest) return

    try {
      await api.acceptInterestChange(user.id, advice.suggested_interest)
      updateInterest(advice.suggested_interest)
      alert("관심 분야가 변경되었습니다.")
      fetchAdvice()
    } catch (error) {
      console.error("Failed to change interest:", error)
      alert("관심 분야 변경에 실패했습니다.")
    }
  }

  const handleChangeLevel = async () => {
    if (!advice || advice.advice_type !== "level_change" || !advice.suggested_level) return

    try {
      await api.acceptLevelChange(user.id, advice.suggested_level)
      updateLevel(advice.suggested_level)
      alert("난이도가 변경되었습니다.")
      fetchAdvice()
    } catch (error) {
      console.error("Failed to change level:", error)
      alert("난이도 변경에 실패했습니다.")
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <NavigationHeader />

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Advice Box */}
        {isLoading && (
          <Card className="mb-8">
            <CardContent className="py-8">
              <p className="text-center text-muted-foreground">조언을 불러오는 중...</p>
            </CardContent>
          </Card>
        )}

        {error && (
          <Card className="mb-8 border-destructive/50">
            <CardContent className="py-8">
              <p className="text-center text-destructive">{error}</p>
            </CardContent>
          </Card>
        )}

        {!isLoading && !error && advice && advice.advice_type !== "none" && (
          <Card className="mb-8 bg-gradient-to-br from-primary/10 to-secondary/10 border-primary/20">
            <CardHeader>
              <div className="flex items-start gap-3">
                <Lightbulb className="h-6 w-6 text-primary mt-1" />
                <div className="flex-1">
                  <CardTitle className="text-lg mb-2">추천 알림</CardTitle>
                  <CardDescription className="text-base leading-relaxed">{advice.reason}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {advice.advice_type === "interest_change" && (
                <Button onClick={handleChangeInterest} variant="secondary">
                  관심 분야 변경하기
                </Button>
              )}
              {advice.advice_type === "level_change" && (
                <Button onClick={handleChangeLevel} variant="secondary">
                  난이도 변경하기
                </Button>
              )}
            </CardContent>
          </Card>
        )}

        {!isLoading && !error && advice && advice.advice_type === "none" && (
          <Card className="mb-8 bg-gradient-to-br from-primary/10 to-secondary/10 border-primary/20">
            <CardHeader>
              <div className="flex items-start gap-3">
                <Lightbulb className="h-6 w-6 text-primary mt-1" />
                <div className="flex-1">
                  <CardTitle className="text-lg mb-2">오늘의 메시지</CardTitle>
                  <CardDescription className="text-base leading-relaxed">{advice.message}</CardDescription>
                </div>
              </div>
            </CardHeader>
          </Card>
        )}

        {/* Navigation Cards */}
        <div className="grid gap-6 md:grid-cols-2">
          <Card
            className="cursor-pointer transition-all hover:shadow-lg hover:border-primary/50 group"
            onClick={() => router.push("/recommendations")}
          >
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-3 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                  <BookOpen className="h-6 w-6 text-primary" />
                </div>
                <CardTitle className="text-xl">오늘 추천 논문</CardTitle>
              </div>
              <CardDescription className="text-base">오늘의 맞춤 논문 3편을 확인하고 학습을 시작하세요</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {user.interest} 분야의{" "}
                {user.level === "beginner" ? "초급" : user.level === "intermediate" ? "중급" : "고급"} 논문
              </p>
            </CardContent>
          </Card>

          <Card
            className="cursor-pointer transition-all hover:shadow-lg hover:border-primary/50 group"
            onClick={() => router.push("/history")}
          >
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-3 rounded-lg bg-secondary/10 group-hover:bg-secondary/20 transition-colors">
                  <History className="h-6 w-6 text-secondary" />
                </div>
                <CardTitle className="text-xl">지금까지 공부한 논문</CardTitle>
              </div>
              <CardDescription className="text-base">학습 이력을 확인하고 복습하세요</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">학습한 논문을 확인하세요</p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}

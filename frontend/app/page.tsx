"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { api } from "@/lib/api"
import { NavigationHeader } from "@/components/navigation-header"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { BookOpen, History, Lightbulb } from "lucide-react"
import { Calendar } from "lucide-react"

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
  const [isAddingToCalendar, setIsAddingToCalendar] = useState(false)
  const [arxivId, setArxivId] = useState("")
  const [isAddingPaper, setIsAddingPaper] = useState(false)

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

  const handleAddToCalendar = async () => {
    setIsAddingToCalendar(true)
    try {
      // 내일 날짜 계산
      const tomorrow = new Date()
      tomorrow.setDate(tomorrow.getDate() + 1)
      const dateString = tomorrow.toISOString().split('T')[0] // YYYY-MM-DD
      
      const response = await api.addToCalendar({
        event_date: dateString
      })
      
      alert(`톡캘린더에 일정이 추가되었습니다! 📅\n${response.event_summary.title}\n${response.event_summary.date}`)
    } catch (error) {
      console.error("Failed to add to calendar:", error)
      alert("톡캘린더 일정 추가에 실패했습니다.")
    } finally {
      setIsAddingToCalendar(false)
    }
  }


  const handleAddPaper = async () => {
    if (!user) return
  
    if (!arxivId.trim()) {
      alert("arXiv ID를 입력해주세요.")
      return
    }

    setIsAddingPaper(true)
    try {
      const response = await api.addPaperByArxivId(arxivId, user.id)
      alert(response.message)
      setArxivId("")
    } catch (error) {
      console.error("Failed to add paper:", error)
      alert("논문 추가에 실패했습니다.")
    } finally {
      setIsAddingPaper(false)
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
        {/* 톡캘린더 버튼 - 오른쪽 상단 */}
        <div className="flex justify-end mb-6">
          <Button 
            variant="outline" 
            onClick={handleAddToCalendar}
            disabled={isAddingToCalendar}
            className="gap-2"
          >
            <Calendar className="h-4 w-4" />
            {isAddingToCalendar ? "추가 중..." : "내일도 Research Mate와 공부하는 일정 톡캘린더에 추가하기 ♡"}
          </Button>
        </div>

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

        {/* 직접 논문 추가하기 Card - 오늘의 메시지 바로 아래 */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="text-lg">직접 공부하고 싶은 논문 추가하기</CardTitle>
            <CardDescription>arXiv ID를 입력하면 논문이 학습 목록에 추가됩니다</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="예: 2005.11401"
                value={arxivId}
                onChange={(e) => setArxivId(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === "Enter") {
                  handleAddPaper()
                  }
                }}
                className="flex-1 px-3 py-2 border border-input rounded-md bg-background"
                disabled={isAddingPaper}
              />
              <Button 
                onClick={handleAddPaper} 
                disabled={isAddingPaper || !arxivId.trim()}
              >
                {isAddingPaper ? "추가 중..." : "추가하기"}
              </Button>
            </div>
          </CardContent>
        </Card>

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

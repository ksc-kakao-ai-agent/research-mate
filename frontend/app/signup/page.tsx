"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const interests = ["RAG", "LLM", "NLP", "Transformer", "Computer Vision", "Reinforcement Learning"]
const difficulties = ["beginner", "intermediate", "advanced"]

export default function SignupPage() {
  const router = useRouter()
  const { signup } = useAuth()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [interest, setInterest] = useState("")
  const [difficulty, setDifficulty] = useState("")
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!username || !password || !confirmPassword) {
      setError("모든 필드를 입력해주세요.")
      return
    }

    if (password !== confirmPassword) {
      setError("비밀번호가 일치하지 않습니다.")
      return
    }

    if (!interest.trim()) {
      setError("관심 분야를 입력해주세요.")
      return
    }

    if (!difficulty) {
      setError("난이도를 선택해주세요.")
      return
    }

    const success = await signup(username, password, interest.trim(), difficulty)

    if (success) {
      router.push("/")
    } else {
      setError("이미 존재하는 아이디입니다.")
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-muted/30">
      <Card className="w-full max-w-lg shadow-sm border-border/60">
        <CardHeader className="space-y-1">
          <CardTitle className="text-3xl font-bold text-center">회원가입</CardTitle>
          <CardDescription className="text-center">논문 추천 서비스를 시작하세요</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="username">아이디</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="아이디를 입력하세요"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">비밀번호</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="비밀번호를 입력하세요"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">비밀번호 확인</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="비밀번호를 다시 입력하세요"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="interest">논문 관심 분야</Label>
              <Input
                id="interest"
                type="text"
                value={interest}
                onChange={(e) => setInterest(e.target.value)}
                placeholder="예: RAG, LLM, Computer Vision 등"
              />
              <p className="text-xs text-muted-foreground">관심있는 논문 분야를 자유롭게 입력해주세요</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="difficulty">원하는 난이도</Label>
              <Select value={difficulty} onValueChange={setDifficulty}>
                <SelectTrigger>
                  <SelectValue placeholder="난이도를 선택하세요" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="beginner">초급</SelectItem>
                  <SelectItem value="intermediate">중급</SelectItem>
                  <SelectItem value="advanced">고급</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button type="submit" className="w-full" size="lg">
              회원가입
            </Button>

            <div className="text-center">
              <Button type="button" variant="link" onClick={() => router.push("/login")}>
                이미 계정이 있으신가요? 로그인
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

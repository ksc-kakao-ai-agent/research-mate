'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import { NavigationHeader } from '@/components/navigation-header'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Separator } from '@/components/ui/separator'
import { ArrowLeft, LogOut, Save, User } from 'lucide-react'

const interests = ['RAG', 'LLM', 'NLP', 'Transformer', 'Computer Vision', 'Reinforcement Learning']

export default function MyPage() {
  const { user, logout, updateProfile } = useAuth()
  const router = useRouter()
  
  const [interestInput, setInterestInput] = useState('')
  const [difficulty, setDifficulty] = useState('')
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    if (!user) {
      router.push('/login')
    } else {
      setInterestInput(user.interest)
      setDifficulty(user.level)
    }
  }, [user, router])

  useEffect(() => {
    if (user) {
      const interestChanged = interestInput !== user.interest
      const difficultyChanged = difficulty !== user.level
      setHasChanges(interestChanged || difficultyChanged)
    }
  }, [interestInput, difficulty, user])

  if (!user) {
    return null
  }



  const handleSave = async () => {
  if (!interestInput) {
    alert('관심 분야를 입력해주세요.')
    return
  }

  try {
    await updateProfile(interestInput, difficulty)  // AuthProvider에서 정의된 함수 호출
    alert('프로필이 성공적으로 업데이트되었습니다.')
    setHasChanges(false)
  } catch (err) {
    console.error(err)
    alert('프로필 업데이트 중 오류가 발생했습니다.')
  }
}

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <div className="min-h-screen bg-background">
      <NavigationHeader />
      
      <main className="container mx-auto px-4 py-8 max-w-3xl">
        <Button
          variant="ghost"
          className="mb-6"
          onClick={() => router.push('/')}
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          홈으로 돌아가기
        </Button>

        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-3 rounded-full bg-primary/10">
              <User className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold">마이페이지</h1>
              <p className="text-muted-foreground">프로필 설정을 관리하세요</p>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* User Info */}
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">계정 정보</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label className="text-muted-foreground">아이디</Label>
                  <span className="font-medium">{user.username}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Preferences */}
          <Card>
            <CardHeader>
              <CardTitle className="text-xl">학습 설정</CardTitle>
              <CardDescription>
                관심 분야와 난이도를 변경하여 맞춤 논문을 추천받으세요
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <Label className="text-base font-semibold">논문 관심 분야</Label>
                  <input
                    type="text"
                    placeholder="관심 분야를 입력하세요"
                    value={interestInput}
                    onChange={(e) => setInterestInput(e.target.value)}
                    className="w-full rounded-md border p-2"
                  />
              </div>

              <Separator />

              <div className="space-y-3">
                <Label htmlFor="difficulty" className="text-base font-semibold">
                  원하는 난이도
                </Label>
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

              {hasChanges && (
                <div className="pt-4">
                  <Button onClick={handleSave} className="w-full" size="lg">
                    <Save className="h-4 w-4 mr-2" />
                    변경사항 저장
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Logout */}
          <Card className="border-destructive/50">
            <CardHeader>
              <CardTitle className="text-xl text-destructive">로그아웃</CardTitle>
              <CardDescription>
                계정에서 로그아웃합니다
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button onClick={handleLogout} variant="destructive" className="w-full" size="lg">
                <LogOut className="h-4 w-4 mr-2" />
                로그아웃
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}

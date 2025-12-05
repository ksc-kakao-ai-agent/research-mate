"use client"

import type React from "react"

import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { api } from "@/lib/api"
import { NavigationHeader } from "@/components/navigation-header"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ArrowLeft, Send, Sparkles } from "lucide-react"

interface Message {
  role: "user" | "assistant"
  content: string
}

export default function ChatPage() {
  const { user } = useAuth()
  const router = useRouter()
  const params = useParams()
  const paperId = Number.parseInt(params.id as string)

  const [paperTitle, setPaperTitle] = useState("")
  const [paperKeywords, setPaperKeywords] = useState<string[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isFetchingPaper, setIsFetchingPaper] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      router.push("/login")
    } else {
      fetchPaperInfo()
    }
  }, [user, router, paperId])

  const fetchPaperInfo = async () => {
    if (!user) return

    setIsFetchingPaper(true)
    setError(null)

    try {
      const data = await api.getPaperDetail(paperId, user.id)
      setPaperTitle(data.title)
      setPaperKeywords(data.metadata.keywords)

      const chatHistory: Message[] = []
      data.chat_history.forEach((chat) => {
        chatHistory.push({ role: "user", content: chat.question })
        chatHistory.push({ role: "assistant", content: chat.answer })
      })

      if (chatHistory.length === 0) {
        chatHistory.push({
          role: "assistant",
          content: `안녕하세요! "${data.title}"에 대해 궁금한 점을 물어보세요. 논문의 내용, 방법론, 결과 등 무엇이든 질문해주시면 상세히 설명해드리겠습니다.`,
        })
      }

      setMessages(chatHistory)
    } catch (error) {
      console.error("Failed to fetch paper info:", error)
      setError("논문 정보를 불러오는데 실패했습니다.")
    } finally {
      setIsFetchingPaper(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = { role: "user", content: input }
    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      const response = await api.chatWithPaper(paperId, user.id, input)

      const aiResponse: Message = {
        role: "assistant",
        content: response.answer,
      }
      setMessages((prev) => [...prev, aiResponse])
    } catch (error) {
      console.error("Failed to send message:", error)
      const errorMessage: Message = {
        role: "assistant",
        content: "죄송합니다. 메시지 전송에 실패했습니다. 다시 시도해주세요.",
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  if (!user) {
    return null
  }

  if (isFetchingPaper) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <NavigationHeader />
        <main className="container mx-auto px-4 py-6 max-w-5xl flex-1 flex items-center justify-center">
          <p className="text-muted-foreground">논문 정보를 불러오는 중...</p>
        </main>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex flex-col">
        <NavigationHeader />
        <main className="container mx-auto px-4 py-6 max-w-5xl flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={() => router.back()}>돌아가기</Button>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <NavigationHeader />

      <main className="container mx-auto px-4 py-6 max-w-5xl flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-6">
          <Button variant="ghost" onClick={() => router.push(`/paper/${paperId}`)}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            논문 상세로 돌아가기
          </Button>
        </div>

        {/* Paper Info */}
        <Card className="mb-4 border-primary/30">
          <CardHeader className="pb-4">
            <div className="flex items-start gap-3">
              <Sparkles className="h-5 w-5 text-primary mt-1 flex-shrink-0" />
              <div>
                <div className="flex items-center gap-2 mb-2">
                  {paperKeywords.map((keyword) => (
                    <Badge key={keyword} variant="secondary">
                      {keyword}
                    </Badge>
                  ))}
                </div>
                <CardTitle className="text-lg leading-snug text-balance">{paperTitle}</CardTitle>
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Chat Messages */}
        <Card className="flex-1 flex flex-col">
          <ScrollArea className="flex-1 p-6">
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`rounded-lg px-4 py-3 max-w-[85%] ${
                      message.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
                    }`}
                  >
                    <p className="text-xs font-medium mb-1 opacity-70">{message.role === "user" ? "나" : "AI 챗봇"}</p>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-muted rounded-lg px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 bg-primary rounded-full animate-bounce"
                        style={{ animationDelay: "0ms" }}
                      />
                      <div
                        className="w-2 h-2 bg-primary rounded-full animate-bounce"
                        style={{ animationDelay: "150ms" }}
                      />
                      <div
                        className="w-2 h-2 bg-primary rounded-full animate-bounce"
                        style={{ animationDelay: "300ms" }}
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Input Area */}
          <CardContent className="border-t border-border p-4">
            <div className="flex items-center gap-2">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="논문에 대해 질문하세요..."
                className="flex-1"
                disabled={isLoading}
              />
              <Button onClick={handleSend} disabled={!input.trim() || isLoading} size="icon">
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}

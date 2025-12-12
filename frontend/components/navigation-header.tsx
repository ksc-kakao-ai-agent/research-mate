'use client'

import { useAuth } from '@/lib/auth-context'
import { Button } from '@/components/ui/button'
import { useRouter } from 'next/navigation'
import { BookOpen, User } from 'lucide-react'

export function NavigationHeader() {
  const { user } = useAuth()
  const router = useRouter()

  const handleLogoClick = () => {
    router.push('/')
  }

  return (
    <header className="border-b border-border bg-card">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div 
          onClick={handleLogoClick}
          className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
        >
          <BookOpen className="h-6 w-6 text-primary" />
          <h1 className="text-xl font-bold">Research Paper Hub</h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted-foreground">{user?.username}</span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push('/mypage')}
          >
            <User className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  )
}
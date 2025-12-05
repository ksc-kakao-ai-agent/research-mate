"use client"

import type React from "react"
import { createContext, useContext, useState, useEffect } from "react"
import { api } from "./api"

interface User {
  id: number
  username: string
  interest: string
  level: string
}

interface AuthContextType {
  user: User | null
  login: (username: string, password: string) => Promise<boolean>
  signup: (username: string, password: string, interest: string, level: string) => Promise<boolean>
  logout: () => void
  updateInterest: (interest: string) => void
  updateLevel: (level: string) => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    const storedUser = localStorage.getItem("user")
    if (storedUser) {
      setUser(JSON.parse(storedUser))
    }
  }, [])

  const signup = async (username: string, password: string, interest: string, level: string) => {
    try {
      const response = await api.register(username, password, interest, level)

      const newUser: User = {
        id: response.user_id,
        username: response.username,
        interest: response.interest,
        level: response.level,
      }

      setUser(newUser)
      localStorage.setItem("user", JSON.stringify(newUser))

      return true
    } catch (error) {
      console.error("Signup failed:", error)
      alert(error instanceof Error ? error.message : "회원가입에 실패했습니다.")
      return false
    }
  }

  const login = async (username: string, password: string) => {
    try {
      const response = await api.login(username, password)

      const loggedInUser: User = {
        id: response.user_id,
        username: response.username,
        interest: response.interest,
        level: response.level,
      }

      setUser(loggedInUser)
      localStorage.setItem("user", JSON.stringify(loggedInUser))

      return true
    } catch (error) {
      console.error("Login failed:", error)
      alert(error instanceof Error ? error.message : "로그인에 실패했습니다.")
      return false
    }
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem("user")
  }

  const updateInterest = (interest: string) => {
    if (user) {
      const updatedUser = { ...user, interest }
      setUser(updatedUser)
      localStorage.setItem("user", JSON.stringify(updatedUser))
    }
  }

  const updateLevel = (level: string) => {
    if (user) {
      const updatedUser = { ...user, level }
      setUser(updatedUser)
      localStorage.setItem("user", JSON.stringify(updatedUser))
    }
  }

  return (
    <AuthContext.Provider value={{ user, login, signup, logout, updateInterest, updateLevel }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

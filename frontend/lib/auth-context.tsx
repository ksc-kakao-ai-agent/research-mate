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

  /** 🔥 새로 추가 */
  updateProfile: (interest: string, level: string) => Promise<boolean>
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

  /** 🔥 서버로 PUT 요청 보내는 updateProfile 추가 */
  const updateProfile = async (interest: string, level: string) => {
  if (!user) return false

  try {
    // user.id와 데이터 객체를 전달
    const response = await api.updateProfile(user.id, { interest, level })

    // 업데이트된 user 반영
    const updatedUser: User = {
      id: user.id,
      username: user.username,
      interest,
      level,
    }

    setUser(updatedUser)
    localStorage.setItem("user", JSON.stringify(updatedUser))

    return true
  } catch (error) {
    console.error("Profile update failed:", error)
    alert(error instanceof Error ? error.message : "프로필 업데이트에 실패했습니다.")
    return false
  }
}


  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        signup,
        logout,
        updateInterest,
        updateLevel,
        updateProfile, // 🔥 반드시 Context에 추가해야 사용 가능
      }}
    >
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

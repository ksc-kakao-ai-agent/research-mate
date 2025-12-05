'use client'

export function PaperGraph() {
  return (
    <div className="w-full h-64 bg-muted/30 rounded-lg border border-border flex items-center justify-center relative overflow-hidden">
      {/* Simple graph visualization */}
      <svg className="w-full h-full" viewBox="0 0 400 200">
        {/* Connections */}
        <line x1="100" y1="100" x2="200" y2="50" stroke="currentColor" strokeWidth="2" className="text-primary/40" />
        <line x1="100" y1="100" x2="200" y2="150" stroke="currentColor" strokeWidth="2" className="text-primary/40" />
        <line x1="300" y1="100" x2="200" y2="50" stroke="currentColor" strokeWidth="2" className="text-primary/40" />
        <line x1="300" y1="100" x2="200" y2="150" stroke="currentColor" strokeWidth="2" className="text-primary/40" />
        
        {/* Nodes */}
        <circle cx="200" cy="50" r="20" fill="currentColor" className="text-primary" />
        <circle cx="200" cy="150" r="20" fill="currentColor" className="text-secondary" />
        <circle cx="100" cy="100" r="25" fill="currentColor" className="text-accent" />
        <circle cx="300" cy="100" r="25" fill="currentColor" className="text-accent" />
        
        {/* Labels */}
        <text x="200" y="55" textAnchor="middle" className="fill-primary-foreground text-xs font-bold">A</text>
        <text x="200" y="155" textAnchor="middle" className="fill-secondary-foreground text-xs font-bold">B</text>
        <text x="100" y="105" textAnchor="middle" className="fill-accent-foreground text-xs font-bold">C</text>
        <text x="300" y="105" textAnchor="middle" className="fill-accent-foreground text-xs font-bold">D</text>
      </svg>
    </div>
  )
}

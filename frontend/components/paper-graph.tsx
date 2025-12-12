'use client'

interface Node {
  id: number
  title: string
  type: "recommended" | "common_reference"
}

interface Edge {
  source: number
  target: number
  type: "cites"
  is_influential: boolean
}

interface PaperGraphProps {
  nodes: Node[]
  edges: Edge[]
}

export default function PaperGraph({ nodes, edges }: PaperGraphProps) {
  // 노드 타입별로 분리
  const recommendedNodes = nodes.filter(n => n.type === "recommended")
  const commonRefNodes = nodes.filter(n => n.type === "common_reference")

  // 추천 논문은 아래쪽에 일렬로 배치
  const recommendedPositions = recommendedNodes.map((node, idx) => ({
    ...node,
    x: 100 + idx * 120, // 간격 120
    y: 150,
  }))

  // 공통 참고문헌은 위쪽 중앙에 배치
  const commonRefPositions = commonRefNodes.map((node, idx) => ({
    ...node,
    x: 200, // 중앙
    y: 50,
  }))

  const allNodePositions = [...recommendedPositions, ...commonRefPositions]

  // 노드 ID로 위치 찾기
  const getNodePosition = (id: number) => allNodePositions.find(n => n.id === id)

  return (
    <div className="w-full h-64 bg-muted/30 rounded-lg border border-border flex items-center justify-center relative overflow-hidden">
      <svg className="w-full h-full" viewBox="0 0 400 200">
        {/* 연결선 그리기 */}
        {edges.map((edge, idx) => {
          const sourcePos = getNodePosition(edge.source)
          const targetPos = getNodePosition(edge.target)
          if (!sourcePos || !targetPos) return null

          return (
            <line
              key={idx}
              x1={sourcePos.x}
              y1={sourcePos.y}
              x2={targetPos.x}
              y2={targetPos.y}
              stroke="currentColor"
              strokeWidth={edge.is_influential ? 3 : 2}
              className={edge.is_influential ? "text-primary/60" : "text-primary/40"}
            />
          )
        })}

        {/* 노드 그리기 */}
        {allNodePositions.map((node) => (
          <g key={node.id}>
            {node.type === "recommended" ? (
              // 오늘 추천 논문 3개
              <>
                <rect
                  x={node.x - 40} // width 80 기준 중앙
                  y={node.y - 20} // height 40 기준 중앙
                  width={80}
                  height={40}
                  rx={10}
                  ry={10}
                  fill="currentColor"
                  className="text-accent"
                />
                <text
                  x={node.x}
                  y={node.y + 5}
                  textAnchor="middle"
                  className="text-xs font-bold fill-accent-foreground"
                >
                  {node.title.length > 5 ? node.title.slice(0, 5) + "..." : node.title}
                </text>
              </>
            ) : (
              // 공통 참고문헌
              <>
                <rect
                  x={node.x - (node.title.length * 7 + 10) / 2} // 글자 길이에 맞춰 중앙 정렬
                  y={node.y - 20}
                  width={node.title.length * 7 + 10}
                  height={40}
                  rx={10}
                  ry={10}
                  fill="currentColor"
                  className="text-primary"
                />
                <text
                  x={node.x}
                  y={node.y + 5}
                  textAnchor="middle"
                  className="text-xs font-bold fill-primary-foreground"
                >
                  {node.title}
                </text>
              </>
            )}
          </g>
        ))}
      </svg>

      {/* 범례 */}
      <div className="absolute bottom-2 right-2 bg-background/80 backdrop-blur-sm rounded px-3 py-2 text-xs space-y-1">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-accent" />
          <span>추천 논문</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-primary" />
          <span>공통 참고문헌</span>
        </div>
      </div>
    </div>
  )
}

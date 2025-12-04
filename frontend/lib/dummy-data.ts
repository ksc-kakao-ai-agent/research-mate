export const dummyAdvice = {
  advice_type: "interest_change" as const,
  current_interest: "NLP",
  suggested_interest: "RAG",
  reason: "최근에 RAG 분야에 관심이 많아지신 것 같아요. 관심 분야를 RAG로 변경할까요?",
}

export const dummyPapers = [
  {
    paper_id: 1,
    title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
    authors: ["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus"],
    abstract:
      "Large pre-trained language models have been shown to store factual knowledge in their parameters, and achieve state-of-the-art results when fine-tuned on downstream NLP tasks. However, their ability to access and precisely manipulate knowledge is still limited, and hence on knowledge-intensive tasks, their performance lags behind task-specific architectures.",
    summary: {
      level: "intermediate",
      content:
        "RAG는 대규모 언어 모델의 한계를 극복하기 위해 외부 지식 검색을 결합한 방법입니다. 모델이 답변을 생성할 때 관련 문서를 먼저 검색하여 참고함으로써 더 정확하고 최신의 정보를 제공할 수 있습니다.",
    },
    metadata: {
      citation_count: 1523,
      citation_velocity: 45.2,
      influential_citation_count: 234,
      keywords: ["RAG", "Retrieval", "NLP"],
    },
    published_date: "2020-05-22",
    source: "arXiv",
    arxiv_id: "2005.11401",
    pdf_url: "https://arxiv.org/pdf/2005.11401.pdf",
    recommended_at: "2024-01-15",
    chat_history: [
      {
        chat_id: 1,
        question: "RAG의 주요 장점은 무엇인가요?",
        answer:
          "RAG의 주요 장점은 세 가지입니다: 1) 외부 지식 베이스를 활용하여 모델의 지식을 확장할 수 있습니다. 2) 최신 정보를 실시간으로 반영할 수 있습니다. 3) 모델의 환각(hallucination)을 줄일 수 있습니다.",
        created_at: "2024-01-15T10:30:00Z",
      },
    ],
  },
  {
    paper_id: 2,
    title: "Attention Is All You Need",
    authors: ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
    abstract:
      "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism.",
    summary: {
      level: "advanced",
      content:
        "트랜스포머 아키텍처를 소개한 획기적인 논문입니다. 어텐션 메커니즘만으로도 시퀀스 처리가 가능함을 보여주었으며, 현대 NLP의 기반이 되었습니다.",
    },
    metadata: {
      citation_count: 85234,
      citation_velocity: 120.5,
      influential_citation_count: 12456,
      keywords: ["Transformer", "Attention", "NLP"],
    },
    published_date: "2017-06-12",
    source: "arXiv",
    arxiv_id: "1706.03762",
    pdf_url: "https://arxiv.org/pdf/1706.03762.pdf",
    recommended_at: "2024-01-14",
    chat_history: [],
  },
  {
    paper_id: 3,
    title: "BERT: Pre-training of Deep Bidirectional Transformers",
    authors: ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee"],
    abstract:
      "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations.",
    summary: {
      level: "intermediate",
      content:
        "BERT는 양방향 트랜스포머를 사용하여 문맥을 양쪽에서 모두 이해하는 언어 모델입니다. 마스킹된 단어를 예측하는 방식으로 학습하여 다양한 NLP 작업에서 높은 성능을 보입니다.",
    },
    metadata: {
      citation_count: 67891,
      citation_velocity: 95.3,
      influential_citation_count: 9876,
      keywords: ["BERT", "NLP", "Transformer"],
    },
    published_date: "2018-10-11",
    source: "arXiv",
    arxiv_id: "1810.04805",
    pdf_url: "https://arxiv.org/pdf/1810.04805.pdf",
    recommended_at: "2024-01-13",
    chat_history: [],
  },
  {
    paper_id: 4,
    title: "Language Models are Few-Shot Learners",
    authors: ["Tom B. Brown", "Benjamin Mann", "Nick Ryder"],
    abstract:
      "Recent work has demonstrated substantial gains on many NLP tasks and benchmarks by pre-training on a large corpus of text followed by fine-tuning on a specific task. This work tests the hypothesis that scaling up language models greatly improves task-agnostic, few-shot performance.",
    summary: {
      level: "advanced",
      content:
        "GPT-3를 소개한 논문으로, 매우 큰 언어 모델이 적은 예시만으로도 다양한 작업을 수행할 수 있음을 보여줍니다. Few-shot learning의 가능성을 입증했습니다.",
    },
    metadata: {
      citation_count: 45678,
      citation_velocity: 78.9,
      influential_citation_count: 7654,
      keywords: ["LLM", "GPT-3", "Few-shot Learning"],
    },
    published_date: "2020-05-28",
    source: "arXiv",
    arxiv_id: "2005.14165",
    pdf_url: "https://arxiv.org/pdf/2005.14165.pdf",
    recommended_at: "2024-01-12",
    chat_history: [],
  },
  {
    paper_id: 5,
    title: "Dense Passage Retrieval for Open-Domain Question Answering",
    authors: ["Vladimir Karpukhin", "Barlas Oguz", "Sewon Min"],
    abstract:
      "Open-domain question answering relies on efficient passage retrieval to select candidate contexts. Traditional sparse vector space models have been the dominant approach for retrieval, but we show that retrieval can be practically implemented using dense representations.",
    summary: {
      level: "intermediate",
      content:
        "질문에 답하기 위해 관련 문서를 효율적으로 찾는 방법을 제안합니다. 밀집 벡터 표현을 사용하여 전통적인 키워드 기반 검색보다 더 의미론적으로 관련된 문서를 찾을 수 있습니다.",
    },
    metadata: {
      citation_count: 3456,
      citation_velocity: 56.7,
      influential_citation_count: 567,
      keywords: ["RAG", "Retrieval", "Question Answering"],
    },
    published_date: "2020-04-10",
    source: "arXiv",
    arxiv_id: "2004.04906",
    pdf_url: "https://arxiv.org/pdf/2004.04906.pdf",
    recommended_at: "2024-01-11",
    chat_history: [],
  },
]

export const SAMPLE_TEX = String.raw`\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{titlesec}
\usepackage{enumitem}
\pagestyle{empty}

\titleformat{\section}{\large\bfseries}{}{0em}{}[\titlerule]

\begin{document}

\begin{center}
  {\LARGE \textbf{Jane Doe}} \\
  jane.doe@example.com $\cdot$ (555) 123-4567 $\cdot$ linkedin.com/in/janedoe
\end{center}

\section*{Skills}
Java, Spring Boot, Kafka, PostgreSQL, AWS, Docker

\section*{Experience}
\textbf{Backend Engineer} --- Example Corp \hfill 2021--Present
\begin{itemize}[leftmargin=*, itemsep=2pt]
  \item Built and maintained microservices using Spring Boot and Kafka.
  \item Migrated legacy batch jobs to event-driven pipelines, cutting latency by 40\%.
\end{itemize}

\section*{Projects}
\textbf{Resume Tailor} --- Personal Project
\begin{itemize}[leftmargin=*, itemsep=2pt]
  \item A web app that tailors a LaTeX resume to a job description automatically.
\end{itemize}

\end{document}
`;

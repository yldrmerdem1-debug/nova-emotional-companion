import { FormEvent, useState } from "react";

import { ChatResponse, sendChatMessage, submitResponseFeedback, SupportMode } from "../api";

type ChatPanelProps = {
  response: ChatResponse | null;
  onResponse: (response: ChatResponse) => void;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
};

type LastExchange = {
  userMessage: string;
  response: ChatResponse;
};

type MoodJournalEntry = {
  id: string;
  mood: string;
  intensity: number;
  supportPreference: string;
  message: string;
};

const supportModes: Array<{ id: SupportMode; title: string; description: string }> = [
  {
    id: "listen",
    title: "Sadece dinle",
    description: "Duyguyu yansıtır, çözüm dayatmaz.",
  },
  {
    id: "think",
    title: "Beraber düşün",
    description: "Önce anlar, sonra küçük adım önerir.",
  },
  {
    id: "brief",
    title: "Kısa cevap",
    description: "Az cümleyle sakin kalır.",
  },
];

export function ChatPanel({ response, onResponse }: ChatPanelProps) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [supportMode, setSupportMode] = useState<SupportMode>("listen");
  const [moodJournal, setMoodJournal] = useState<MoodJournalEntry[]>([]);
  const [lastExchange, setLastExchange] = useState<LastExchange | null>(null);
  const [feedbackMode, setFeedbackMode] = useState<"idle" | "correcting" | "saved">("idle");
  const [idealReply, setIdealReply] = useState("");
  const [feedbackNotes, setFeedbackNotes] = useState("");
  const brainState = response?.brain_state;
  const emotionalSummary = response?.emotional_context?.emotional_summary;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await sendMessage(message);
  }

  async function sendMessage(nextMessage: string) {
    const trimmedMessage = nextMessage.trim();
    if (!trimmedMessage) return;

    setIsSending(true);
    setError(null);
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text: trimmedMessage },
    ]);

    try {
      const nextResponse = await sendChatMessage({
        message: trimmedMessage,
        support_mode: supportMode,
      });
      onResponse(nextResponse);
      recordMoodEntry(trimmedMessage, nextResponse);
      setLastExchange({ userMessage: trimmedMessage, response: nextResponse });
      setFeedbackMode("idle");
      setIdealReply("");
      setFeedbackNotes("");
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: nextResponse.reply,
        },
      ]);
      setMessage("");
    } catch (caughtError) {
      if (caughtError instanceof TypeError && caughtError.message === "Failed to fetch") {
        setError("Backend'e ulaşılamadı. 8000 portundaki API açık mı kontrol et.");
      } else {
        setError(caughtError instanceof Error ? caughtError.message : "Something went wrong.");
      }
    } finally {
      setIsSending(false);
    }
  }

  function recordMoodEntry(userMessage: string, nextResponse: ChatResponse) {
    const summary = nextResponse.emotional_context?.emotional_summary;
    const latestMood = summary?.mood_timeline?.at(-1);
    const mood = latestMood?.mood ?? nextResponse.brain_state.emotion ?? "unknown";
    const intensity = latestMood?.intensity ?? 0.1;
    const supportPreference = summary?.support_preference ?? supportMode;
    setMoodJournal((current) => [
      {
        id: crypto.randomUUID(),
        mood,
        intensity,
        supportPreference,
        message: userMessage,
      },
      ...current,
    ].slice(0, 7));
  }

  async function saveFeedback(rating: "good" | "bad") {
    if (!lastExchange) return;
    setError(null);

    try {
      await submitResponseFeedback({
        user_message: lastExchange.userMessage,
        brain_state: lastExchange.response.brain_state,
        robot_reply: lastExchange.response.reply,
        rating,
        ideal_reply: rating === "bad" ? idealReply : undefined,
        notes: rating === "bad" ? feedbackNotes : undefined,
        response_meta: lastExchange.response.response_meta,
      });
      setFeedbackMode("saved");
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Feedback kaydedilemedi.");
    }
  }

  return (
    <section className="chat-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Emotional companion</p>
          <h2>Bugün nasılsın?</h2>
        </div>
        <div className="header-badges">
          <span className="status-pill">{isSending ? "Düşünüyor..." : "Hazır"}</span>
          <span className={`privacy-badge ${brainState?.memory_allowed === false ? "shared" : "private"}`}>
            {brainState ? `hafıza ${brainState.memory_allowed ? "açık" : "kapalı"}` : "hafıza bekliyor"}
          </span>
        </div>
      </div>

      <section className="support-mode-card" aria-label="Konuşma modu">
        <div>
          <p className="eyebrow">Konuşma modu</p>
          <p className="support-mode-copy">Nasıl yanında durmamı istediğini seç.</p>
        </div>
        <div className="support-mode-grid">
          {supportModes.map((mode) => (
            <button
              key={mode.id}
              type="button"
              className={supportMode === mode.id ? "mode-active" : ""}
              onClick={() => setSupportMode(mode.id)}
            >
              <strong>{mode.title}</strong>
              <span>{mode.description}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="conversation-feed" aria-label="Chat messages">
        {messages.length ? (
          messages.map((chatMessage) => (
            <article key={chatMessage.id} className={`message-bubble ${chatMessage.role}`}>
              <span>{chatMessage.role === "user" ? "You" : "Robot"}</span>
              <p>{chatMessage.text}</p>
            </article>
          ))
        ) : (
          <article className="empty-chat">
            <p>İstersen sadece içini dök. Nova önce dinler, çözüm istemezsen çözüm dayatmaz.</p>
          </article>
        )}
        {isSending && (
          <article className="message-bubble assistant">
            <span>Robot</span>
            <p>Düşünüyor...</p>
          </article>
        )}
      </section>

      <form className="composer" onSubmit={handleSubmit}>
        <input
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Bugün biraz kötüyüm, sadece dinle."
          disabled={isSending}
        />
        <button type="submit" disabled={!message.trim() || isSending}>
          Gönder
        </button>
      </form>

      {error && <p className="error-message">{error}</p>}

      <section className="response-card">
        <p className="eyebrow">Son destek cevabı</p>
        <p className="speech-text">
          {response?.reply ?? "Henüz cevap yok."}
        </p>
      </section>

      {(emotionalSummary || moodJournal.length > 0) && (
        <section className="journal-card">
          <div className="journal-header">
            <div>
              <p className="eyebrow">Duygu günlüğü</p>
              <h3>Son 7 konuşma izi</h3>
            </div>
            <span>{emotionalSummary?.dominant_mood ?? "yeni"}</span>
          </div>
          <div className="journal-list">
            {moodJournal.length ? (
              moodJournal.map((entry) => (
                <article key={entry.id} className="journal-entry">
                  <strong>{entry.mood}</strong>
                  <span>{Math.round(entry.intensity * 100)}% yoğunluk</span>
                  <small>{entry.supportPreference} · {entry.message}</small>
                </article>
              ))
            ) : (
              <p className="support-mode-copy">Duygu izi oluşması için bir mesaj gönder.</p>
            )}
          </div>
          {emotionalSummary?.care_suggestions?.length ? (
            <p className="journal-suggestion">{emotionalSummary.care_suggestions[0]}</p>
          ) : null}
        </section>
      )}

      {lastExchange && (
        <section className="feedback-card">
          <p className="eyebrow">Robotu eğit</p>
          <p className="feedback-copy">Bu cevap yanında duruş olarak iyi miydi? Kötüyse nasıl duymak istediğini yaz.</p>
          <div className="feedback-actions">
            <button type="button" onClick={() => saveFeedback("good")} disabled={feedbackMode === "saved"}>
              İyi cevap
            </button>
            <button type="button" className="ghost-button" onClick={() => setFeedbackMode("correcting")}>
              Kötü, düzelteceğim
            </button>
          </div>

          {feedbackMode === "correcting" && (
            <div className="correction-box">
              <textarea
                value={idealReply}
                onChange={(event) => setIdealReply(event.target.value)}
                placeholder="Bu durumda robot ne demeliydi?"
                rows={3}
              />
              <input
                value={feedbackNotes}
                onChange={(event) => setFeedbackNotes(event.target.value)}
                placeholder="Neden kötüydü? (opsiyonel)"
              />
              <button type="button" onClick={() => saveFeedback("bad")} disabled={!idealReply.trim()}>
                Düzeltmeyi kaydet
              </button>
            </div>
          )}

          {feedbackMode === "saved" && <p className="feedback-saved">Kaydedildi. Bu tercih sonraki cevapları iyileştirecek.</p>}
        </section>
      )}
    </section>
  );
}

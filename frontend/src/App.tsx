import { useState } from "react";

import type { ChatResponse } from "./api";
import { AvatarFace } from "./components/AvatarFace";
import { ChatPanel } from "./components/ChatPanel";

export default function App() {
  const [chatResponse, setChatResponse] = useState<ChatResponse | null>(null);

  function handleResponse(response: ChatResponse) {
    setChatResponse(response);
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <p className="eyebrow">Türkçe emotional companion</p>
        <h1>Yargısız dinleyen sakin alan</h1>
        <p className="hero-copy">
          Nova terapi yerine geçmez; ama günlük duygu takibi, iç dökme ve düşük baskılı konuşma için yanında durur.
        </p>
      </section>

      <div className="workspace">
        <AvatarFace
          robotState={chatResponse?.brain_state.robot_state}
          brainState={chatResponse?.brain_state}
        />
        <ChatPanel
          response={chatResponse}
          onResponse={handleResponse}
        />
      </div>
    </main>
  );
}

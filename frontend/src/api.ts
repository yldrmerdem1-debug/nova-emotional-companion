export type ContextMode =
  | "private"
  | "public"
  | "friends_present"
  | "family_present"
  | "unknown_people_present";

const API_BASE_URL = "http://127.0.0.1:8000";

export type SupportMode = "listen" | "think" | "brief";

export type ChatRequest = {
  user_id?: string;
  conversation_id?: string;
  message: string;
  present_people?: string[];
  context_mode?: ContextMode;
  scene_context?: string;
  companion_name?: string;
  support_mode?: SupportMode;
};

export type RobotState = {
  emotion: string;
  face: string;
  eyes: string;
  mouth: string;
  voice_tone: string;
  body_action: string;
  head_motion: string;
  eye_contact: string;
  movement_intensity: string;
  should_speak: boolean;
};

export type BrainState = {
  route: string;
  emotion: string;
  need: string;
  tone: string;
  style: string;
  memory_allowed: boolean;
  robot_state: RobotState;
  model_version: string;
  loaded_models: string[];
};

export type MindWorkspace = {
  attention?: {
    top_signal?: {
      type?: string;
      reason?: string;
      score?: number;
    };
  };
  contradictions?: {
    has_contradiction?: boolean;
    max_severity?: string;
    contradictions?: unknown[];
  };
  causal_graph?: {
    causal_summary?: string;
    nodes?: unknown[];
    edges?: unknown[];
  };
  goal_stack?: {
    active_goal?: {
      horizon?: string;
      goal?: string;
      priority?: number;
    };
  };
  metacognition?: {
    confidence?: number;
    uncertainty?: number;
    recommended_actions?: string[];
  };
  memory_consolidation?: {
    user_model_summary?: string;
    project_model_summary?: string;
    themes?: string[];
  };
  self_explanation?: {
    compact?: string;
  };
  final_policy?: {
    action?: string;
    reason?: string;
  };
};

export type MemoryUpdate = {
  type: string;
  content: string;
  importance: number;
  privacy: string;
  related_people?: string[] | null;
};

export type ChatResponse = {
  conversation_id?: string;
  message?: string;
  reply: string;
  brain_state: BrainState;
  speech?: string;
  robot_state?: RobotState;
  memory_updates?: MemoryUpdate[];
  privacy_notes?: string[];
  used_memories?: string[];
  memory_context?: {
    retrieved_memories: unknown[];
    saved_memories: unknown[];
    profile_summary: Record<string, unknown>;
  };
  emotional_context?: {
    saved_emotional_record?: unknown;
    emotional_summary?: {
      dominant_mood?: string;
      support_preference?: string;
      mood_timeline?: Array<{
        mood?: string;
        intensity?: number;
        created_at?: string;
        trigger_terms?: string[];
      }>;
      care_suggestions?: string[];
    };
  };
  response_meta?: {
    intent: string;
    strategy: string;
    confidence: number;
    source: string;
    local_llm?: unknown;
    vocabulary?: unknown;
    long_context?: unknown;
  };
  mind_workspace?: MindWorkspace;
};

export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: payload.message, support_mode: payload.support_mode ?? "listen" }),
  });

  if (!response.ok) {
    throw new Error("Failed to send chat message");
  }

  return response.json();
}

export type ResponseFeedbackPayload = {
  user_message: string;
  brain_state: BrainState;
  robot_reply: string;
  rating: "good" | "bad";
  ideal_reply?: string;
  notes?: string;
  response_meta?: ChatResponse["response_meta"];
};

export async function submitResponseFeedback(payload: ResponseFeedbackPayload): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/training/response-feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error("Failed to save response feedback");
  }
}

export async function transcribeAudio(audio: Blob): Promise<{ text: string; language: string }> {
  const formData = new FormData();
  formData.append("file", audio, "voice-message.webm");

  const response = await fetch(`${API_BASE_URL}/voice/transcribe`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to transcribe audio");
  }

  return response.json();
}

export async function speakText(
  text: string,
  voice = "default",
): Promise<{ audio_url: string; audio_base64: string; message?: string }> {
  const response = await fetch(`${API_BASE_URL}/voice/speak`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voice }),
  });

  if (!response.ok) {
    throw new Error("Failed to synthesize speech");
  }

  return response.json();
}

export type DebugResource = "memories" | "people" | "events";

export async function loadDebugResource(
  userId: string,
  resource: DebugResource,
): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/users/${userId}/${resource}`);

  if (!response.ok) {
    throw new Error(`Failed to load ${resource}`);
  }

  return response.json();
}

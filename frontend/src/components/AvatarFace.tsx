import type { BrainState, RobotState } from "../api";

type AvatarFaceProps = {
  robotState?: RobotState;
  brainState?: BrainState;
};

type AvatarExpression = "neutral" | "focused" | "concerned" | "happy" | "serious";

function getAvatarExpression(robotState?: RobotState, brainState?: BrainState): AvatarExpression {
  if (brainState?.route === "privacy_boundary") return "serious";
  if (!robotState) return "neutral";
  if (robotState.face === "focused") return "focused";
  if (robotState.face === "soft_concerned") return "concerned";
  if (robotState.face === "happy" || robotState.face === "playful") return "happy";
  if (robotState.face === "serious") return "serious";
  if (robotState.emotion === "focused") return "focused";
  if (robotState.emotion === "sad" || robotState.emotion === "concerned") return "concerned";
  if (robotState.emotion === "excited" || robotState.emotion === "playful") return "happy";
  if (robotState.emotion === "serious" || robotState.emotion === "frustrated") return "serious";

  const face = robotState.face.toLowerCase();
  if (face.includes("focused")) return "focused";
  if (face.includes("concerned") || face.includes("sad")) return "concerned";
  if (face.includes("happy") || face.includes("smile") || face.includes("playful")) {
    return "happy";
  }
  if (face.includes("serious")) return "serious";

  return "neutral";
}

function getActionClasses(robotState?: RobotState) {
  const bodyAction = robotState?.body_action.toLowerCase() ?? "";
  const headMotion = robotState?.head_motion.toLowerCase() ?? "";
  const voiceTone = robotState?.voice_tone.toLowerCase() ?? "";
  const emotion = robotState?.emotion.toLowerCase() ?? "";
  const classes = [];

  if (bodyAction.includes("look_at_user")) classes.push("action-look-at-user");
  if (bodyAction.includes("slight_head_tilt")) classes.push("action-slight-head-tilt");
  if (headMotion === "tilt_left") classes.push("head-tilt-left");
  if (headMotion === "tilt_right") classes.push("head-tilt-right");
  if (headMotion === "nod_once" || bodyAction.includes("small_nod")) classes.push("head-nod-once");
  if (voiceTone === "calm_confident") classes.push("tone-calm-confident");
  if (emotion === "excited" || robotState?.movement_intensity === "high") classes.push("energy-high");
  if (robotState?.eyes) classes.push(`eyes-${robotState.eyes.replaceAll("_", "-")}`);
  if (robotState?.mouth) classes.push(`mouth-${robotState.mouth.replaceAll("_", "-")}`);
  if (robotState?.eye_contact) classes.push(`eye-contact-${robotState.eye_contact}`);
  if (robotState?.should_speak === false) classes.push("silent-mode");

  return classes;
}

export function AvatarFace({ robotState, brainState }: AvatarFaceProps) {
  const expression = getAvatarExpression(robotState, brainState);
  const emotion = robotState?.emotion ?? "idle";
  const actionClasses = getActionClasses(robotState);
  const className = [
    "avatar-card",
    `expression-${expression}`,
    ...actionClasses,
  ].join(" ");

  return (
    <section className={className} aria-label={`Avatar emotion: ${emotion}`}>
      <div className="avatar-orb">
        <div className="avatar-glow" />
        <div className="avatar-head">
          <div className="avatar-brow left" />
          <div className="avatar-brow right" />
          <div className="avatar-eyes">
            <span className="avatar-eye left">
              <span className="avatar-pupil" />
              <span className="avatar-shine" />
            </span>
            <span className="avatar-eye right">
              <span className="avatar-pupil" />
              <span className="avatar-shine" />
            </span>
          </div>
          <div className="avatar-mouth" />
        </div>
      </div>
      <div className="avatar-readout">
        <p className="eyebrow">Avatar state</p>
        <h2>{expression}</h2>
        <p>{robotState ? `${robotState.eyes} / ${robotState.mouth}` : "idle_face"}</p>
        {brainState && <span className="route-chip">{brainState.route}</span>}
      </div>
    </section>
  );
}

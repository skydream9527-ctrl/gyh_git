import type { AgentCard } from "@/types/api";
import "./WelcomeScreen.css";

interface WelcomeScreenProps {
  agent: AgentCard | null;
  onSendStarter: (text: string) => void;
}

/**
 * Workspace empty-state welcome screen.
 * Shows the Agent's identity and clickable starter prompts
 * so the user knows what to ask on first interaction.
 */
export function WelcomeScreen({ agent, onSendStarter }: WelcomeScreenProps) {
  if (!agent) return null;

  const starters = agent.starters || [];
  const description = agent.user_friendly_description || agent.description || "";

  return (
    <div className="ws-welcome">
      <div className="ws-welcome-icon" style={{ background: `${agent.color}18`, color: agent.color }}>
        {agent.icon}
      </div>
      <h2 className="ws-welcome-title">
        {agent.name}
      </h2>
      {description && (
        <p className="ws-welcome-desc">{description}</p>
      )}
      {starters.length > 0 && (
        <div className="ws-welcome-starters">
          <p className="ws-welcome-hint">你可以这样问我：</p>
          <div className="ws-welcome-starter-grid">
            {starters.map((text, i) => (
              <button
                key={i}
                type="button"
                className="ws-welcome-starter"
                onClick={() => onSendStarter(text)}
              >
                <span className="ws-welcome-starter-icon">💡</span>
                <span className="ws-welcome-starter-text">{text}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

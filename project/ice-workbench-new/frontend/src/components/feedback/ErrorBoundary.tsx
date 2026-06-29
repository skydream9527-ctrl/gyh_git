import { Component, ReactNode } from "react";
import { reportError } from "@/lib/errorReporter";
import { ErrorState } from "./ErrorState";

interface Props {
  children: ReactNode;
  /** Optional label for logging (e.g., "admin" to distinguish nested boundaries). */
  region?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * React error boundary — catches render/lifecycle errors in children,
 * reports them via errorReporter, and renders a fallback UI so the entire
 * page doesn't go blank.
 *
 * Usage:
 *   <ErrorBoundary region="workspace">
 *     <WorkspacePage />
 *   </ErrorBoundary>
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    reportError(error, {
      context: {
        region: this.props.region,
        componentStack: info.componentStack?.slice(0, 500),
      },
    });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  private handleHome = () => {
    window.location.href = "/dashboard";
  };

  render() {
    if (this.state.hasError) {
      return (
        <ErrorState
          icon="🚨"
          title="页面渲染出错"
          description={this.state.error?.message || "发生了未预期的错误"}
          errorCode="RENDER_ERROR"
          actions={
            <div style={{ display: "flex", gap: 12 }}>
              <button className="btn btn-primary" onClick={this.handleReset}>
                重试
              </button>
              <button className="btn" onClick={this.handleHome}>
                回到首页
              </button>
            </div>
          }
        />
      );
    }
    return this.props.children;
  }
}

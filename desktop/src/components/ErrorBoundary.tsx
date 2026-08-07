import { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught React Error caught by ErrorBoundary:", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-screen w-screen flex-col items-center justify-center bg-[#020408] text-rose-400 font-mono p-6 select-none">
          <div className="max-w-xl w-full border border-rose-600/80 bg-[#090204] p-6 shadow-[0_0_40px_rgba(244,63,94,0.25)] space-y-4">
            <div className="flex items-center justify-between border-b border-rose-900/60 pb-3">
              <div className="flex items-center space-x-2">
                <span className="text-rose-500 font-bold text-sm tracking-wider animate-pulse">
                  [ ⚠ CRITICAL SYSTEM FAULT ]
                </span>
              </div>
              <span className="text-xs text-rose-700 font-bold">ERROR_BOUNDARY</span>
            </div>

            <div className="font-mono text-xs text-rose-300 leading-relaxed bg-black/60 p-3 border border-rose-950/80 overflow-x-auto max-h-40">
              <p className="font-bold text-rose-400 mb-1">
                {this.state.error ? this.state.error.toString() : "Unknown Error Occurred"}
              </p>
              {this.state.errorInfo && (
                <pre className="text-[10px] text-rose-600 whitespace-pre-wrap">
                  {this.state.errorInfo.componentStack}
                </pre>
              )}
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={this.handleReset}
                className="px-3 py-1.5 border border-cyan-800 bg-cyan-950/40 text-cyan-300 text-xs hover:border-[#00e5ff] hover:text-[#00e5ff] transition-colors cursor-pointer"
              >
                [ ATTEMPT RECOVERY ]
              </button>
              <button
                type="button"
                onClick={this.handleReload}
                className="px-4 py-1.5 border border-rose-600 bg-rose-600 text-[#020408] font-bold text-xs hover:bg-transparent hover:text-rose-400 transition-colors cursor-pointer"
              >
                [ REBOOT INTERFACE ↵ ]
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export function PanelState({ children, tone = "normal" }) {
  return (
    <div className={`panel-state ${tone === "error" ? "error-state" : ""}`}>
      {children}
    </div>
  );
}

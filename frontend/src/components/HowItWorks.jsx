import { howItWorksSteps } from "../data/homeContent";
import { SectionHeader } from "./SectionHeader";

export function HowItWorks() {
  return (
    <section className="content-section">
      <SectionHeader
        eyebrow="How it works"
        title="Built for rough movie memory"
        description="This is a ranked retrieval app, so the interface stays focused on search and film inspection."
      />

      <div className="process-list">
        {howItWorksSteps.map((step, index) => (
          <article className="process-card" key={step.title}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

import { useState } from "react";

import { faqItems } from "../data/homeContent";
import { SectionHeader } from "./SectionHeader";

export function FaqSection() {
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <section className="content-section faq-section">
      <SectionHeader
        eyebrow="FAQ"
        title="Frequently asked questions"
        description="These answers match the current local project and data."
      />

      <div className="faq-list">
        {faqItems.map((item, index) => (
          <article
            className="faq-item"
            key={item.question}
          >
            <button
              type="button"
              onClick={() => setOpenIndex(openIndex === index ? -1 : index)}
            >
              <span>{item.question}</span>
              <span>{openIndex === index ? "-" : "+"}</span>
            </button>

            {openIndex === index && <p>{item.answer}</p>}
          </article>
        ))}
      </div>
    </section>
  );
}

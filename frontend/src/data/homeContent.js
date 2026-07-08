export const exampleQueries = [
  "A ship that sinks after hitting an iceberg",
  "A boxer who trains in Philadelphia",
  "A green ogre who lives in a swamp",
  "A man wakes up with tattoos and memory loss",
];

export const faqItems = [
  {
    question: "How do I find a movie if I only remember a scene?",
    answer:
      "Write the scene like you would explain it to a friend. Include the place, object, character, ending, or any strange moment you remember.",
  },
  {
    question: "Can I search by exact movie title?",
    answer:
      "Yes. Exact-title searches use the same search box. If a title looks missing locally, the backend can try the TMDB title fallback.",
  },
  {
    question: "Why do some cards not show posters?",
    answer:
      "The CMU dataset does not include posters. Posters appear only when the movie has TMDB metadata or was imported from TMDB.",
  },
  {
    question: "What can I see in movie details?",
    answer:
      "The detail view shows fields your database actually has: title, year, genres, plot summary, runtime, revenue, source, language, country, and external IDs.",
  },
];

export const howItWorksSteps = [
  {
    title: "Describe what you remember",
    body:
      "Use a rough plot, a character clue, a famous object, or the exact title.",
  },
  {
    title: "Hybrid search ranks matches",
    body:
      "The backend combines full-text, vector, broad lexical, and memory clue results.",
  },
  {
    title: "Open the best cards",
    body:
      "Click any result or film card to inspect the stored movie details.",
  },
  {
    title: "Missing titles can be imported",
    body:
      "For title-like searches, TMDB fallback can add the movie locally for next time.",
  },
];

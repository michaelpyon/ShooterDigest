declare module "vader-sentiment" {
  interface SentimentScores {
    neg: number;
    neu: number;
    pos: number;
    compound: number;
  }

  const SentimentIntensityAnalyzer: {
    polarity_scores(text: string): SentimentScores;
  };

  export default { SentimentIntensityAnalyzer };
}

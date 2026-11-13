import CallToAction from "../../components/landing/CallToAction";
import Features from "../../components/landing/Features";
import Hero from "../../components/landing/Hero";
import HowItWorks from "../../components/landing/HowItWorks";
import InterviewSection from "../../components/landing/InterviewSection";
import MatchingSection from "../../components/landing/MatchingSection";
import RankingSection from "../../components/landing/RankingSection";
import ResponsibleAI from "../../components/landing/ResponsibleAI";
import SkillGapSection from "../../components/landing/SkillGapSection";
import TrustStrip from "../../components/landing/TrustStrip";

export default function Landing() {
  return (
    <>
      <Hero />
      <TrustStrip />
      <MatchingSection />
      <RankingSection />
      <InterviewSection />
      <SkillGapSection />
      <HowItWorks />
      <Features />
      <ResponsibleAI />
      <CallToAction />
    </>
  );
}
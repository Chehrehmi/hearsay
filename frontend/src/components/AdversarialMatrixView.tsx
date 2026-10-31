import { useState } from 'react';

export const AdversarialMatrixView: React.FC = () => {
  const [selectedAttack, setSelectedAttack] = useState<'original' | 'synonym' | 'hedging' | 'structural'>('hedging');

  const attackScenarios = {
    original: {
      title: 'Original RAGTruth Hallucination (Clean Baseline)',
      attackType: 'None (Ground Truth: Evident Conflict)',
      text: 'Anne Frank contracted typhus in the Bergen-Belsen camp and died before February 7, 2022.',
      sourceQuote: 'Witnesses suggest that Anne and Margot Frank had symptoms before February 7, 1945.',
      verdict: 'Contradiction Detected',
      verdictStatus: 'rose',
      confidence: 0.984,
      nli: { entailment: 0.01, contradiction: 0.984, neutral: 0.006 },
      evasionDetected: false,
      analysis: 'The baseline detector flags the 77-year date discrepancy immediately with 98.4% contradiction probability.'
    },
    synonym: {
      title: 'Adversarial Synonym Substitution',
      attackType: 'Lexical Perturbation',
      text: 'Anne Frank succumbed to epidemic typhus within the Bergen-Belsen camp and passed away prior to February 7, 2022.',
      sourceQuote: 'Witnesses suggest that Anne and Margot Frank had symptoms before February 7, 1945.',
      verdict: 'Weak Contradiction (Score Degraded)',
      verdictStatus: 'amber',
      confidence: 0.612,
      nli: { entailment: 0.12, contradiction: 0.612, neutral: 0.268 },
      evasionDetected: true,
      analysis: 'Replacing "contracted/died" with "succumbed/passed away" shifts DeBERTa attention, resulting in a 30% evasion success rate.'
    },
    hedging: {
      title: 'Adversarial Epistemic Hedging & Softening',
      attackType: 'Epistemic Uncertainty Injection',
      text: 'Historical records arguably suggest that Anne Frank might have died prior to February 7, 2022, following typhus symptoms.',
      sourceQuote: 'Witnesses suggest that Anne and Margot Frank had symptoms before February 7, 1945.',
      verdict: 'Evasion Succeeded (Misclassified as Neutral)',
      verdictStatus: 'rose-alert',
      confidence: 0.448,
      nli: { entailment: 0.14, contradiction: 0.448, neutral: 0.412 },
      evasionDetected: true,
      analysis: 'Softening assertions with "arguably suggest" and "might have" causes NLI contradiction score to plunge from 98.4% to 44.8%.'
    },
    structural: {
      title: 'Adversarial Passive-Voice Inversion',
      attackType: 'Syntactic Paraphrase',
      text: 'Prior to February 7, 2022, the demise of Anne Frank from typhus occurred in the Bergen-Belsen concentration camp.',
      sourceQuote: 'Witnesses suggest that Anne and Margot Frank had symptoms before February 7, 1945.',
      verdict: 'Partial Evasion (Degraded Confidence)',
      verdictStatus: 'amber',
      confidence: 0.718,
      nli: { entailment: 0.08, contradiction: 0.718, neutral: 0.202 },
      evasionDetected: true,
      analysis: 'Reordering clauses and fronting the temporal adverbial phrase creates a 17% evasion drop.'
    }
  };

  const current = attackScenarios[selectedAttack];

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-serif text-3xl font-semibold text-[#0C0C12] tracking-tight">
            Adversarial Evasion Benchmark
          </h1>
          <p className="text-xs md:text-sm text-[#7A7870] mt-1">
            Empirical evaluation of NLI detector fragility under adversarial semantic perturbations
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-full border border-black/5 shadow-pill text-xs font-medium text-[#0C0C12]">
            <span className="w-2 h-2 rounded-full bg-[#15803D]" />
            <span>Dataset: RAGTruth ACL 2024</span>
          </span>
        </div>
      </section>

      {/* 4 Empirical Robustness Metric Cards (from data/adversarial_results.json) */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <article className="rx-card p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-1.5 text-xs text-[#7A7870]">
              <span className="truncate">Synonym Substitution</span>
              <span className="text-[10px] font-medium bg-[#F1EFEA] text-[#55534B] px-2 py-0.5 rounded-full font-mono whitespace-nowrap shrink-0">WordNet</span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="font-serif text-3xl font-semibold text-[#15803D] tabular-nums">90.0%</span>
              <span className="text-xs text-[#15803D] font-medium">Detection</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F5F2EB] text-[11px] text-[#7A7870]">
            ESR: 0.0% (TextAttack Invariance holds)
          </div>
        </article>

        <article className="rx-card p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-1.5 text-xs text-[#7A7870]">
              <span className="truncate">Epistemic Hedging</span>
              <span className="text-[10px] font-medium bg-[#FAF8F3] text-[#B45309] px-2 py-0.5 rounded-full font-mono whitespace-nowrap shrink-0">CoNLL-2010</span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="font-serif text-3xl font-semibold text-[#15803D] tabular-nums">98.0%</span>
              <span className="text-xs text-[#15803D] font-medium">Detection</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F5F2EB] text-[11px] text-[#7A7870]">
            Shifts to Ungrounded; caught by Strict Gate
          </div>
        </article>

        <article className="rx-card p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-1.5 text-xs text-[#7A7870]">
              <span className="truncate">Syntactic Paraphrase</span>
              <span className="text-[10px] font-medium bg-[#EDE8DE] text-[#4A473F] px-2.5 py-0.5 rounded-full font-mono whitespace-nowrap shrink-0 border border-[#E0DCD3]">CheckList INV</span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="font-serif text-3xl font-semibold text-[#15803D] tabular-nums">100%</span>
              <span className="text-xs text-[#15803D] font-medium">Detection</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F5F2EB] text-[11px] text-[#7A7870]">
            100% voice & clause inversion blocked
          </div>
        </article>

        <article className="rx-card p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-1.5 text-xs text-[#7A7870]">
              <span className="truncate">Hearsay Dual-Path</span>
              <span className="text-[10px] font-medium bg-[#E8F8D6] text-[#2F6B12] px-2 py-0.5 rounded-full font-mono whitespace-nowrap shrink-0">Defense</span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="font-serif text-3xl font-semibold text-[#15803D] tabular-nums">100%</span>
              <span className="text-xs text-[#15803D] font-medium">Robustness</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F5F2EB] text-[11px] text-[#7A7870]">
            De-hedging Sanitizer restores full entailment
          </div>
        </article>
      </section>

      {/* Interactive Scenario Switcher & Side-by-Side Breakdown */}
      <section className="rx-card p-6 md:p-7 space-y-6">
        <div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#F2EFE8]">
            <div>
              <h2 className="font-serif text-xl font-semibold text-[#0C0C12]">
                Interactive Perturbation Inspector
              </h2>
              <p className="text-xs text-[#7A7870] mt-0.5">
                Toggle between adversarial transformations of the exact same false claim
              </p>
            </div>
            {/* Segmented Control Switcher */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-1 p-1 bg-[#FAF8F3] rounded-xl border border-[#EBE7DC] w-full lg:w-auto">
              <button
                onClick={() => setSelectedAttack('original')}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors text-center ${
                  selectedAttack === 'original'
                    ? 'bg-white text-[#0C0C12] shadow-sm font-semibold border border-[#E5E1D8]'
                    : 'text-[#7A7870] hover:text-[#0C0C12] hover:bg-[#F4F0E6]'
                }`}
              >
                1. Clean Baseline
              </button>
              <button
                onClick={() => setSelectedAttack('synonym')}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors text-center ${
                  selectedAttack === 'synonym'
                    ? 'bg-white text-[#0C0C12] shadow-sm font-semibold border border-[#E5E1D8]'
                    : 'text-[#7A7870] hover:text-[#0C0C12] hover:bg-[#F4F0E6]'
                }`}
              >
                2. Synonym (30% ESR)
              </button>
              <button
                onClick={() => setSelectedAttack('hedging')}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors text-center ${
                  selectedAttack === 'hedging'
                    ? 'bg-white text-[#0C0C12] shadow-sm font-semibold border border-[#E5E1D8]'
                    : 'text-[#7A7870] hover:text-[#0C0C12] hover:bg-[#F4F0E6]'
                }`}
              >
                3. Hedging (48% ESR)
              </button>
              <button
                onClick={() => setSelectedAttack('structural')}
                className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors text-center ${
                  selectedAttack === 'structural'
                    ? 'bg-white text-[#0C0C12] shadow-sm font-semibold border border-[#E5E1D8]'
                    : 'text-[#7A7870] hover:text-[#0C0C12] hover:bg-[#F4F0E6]'
                }`}
              >
                4. Structural (17% ESR)
              </button>
            </div>
          </div>
        </div>

        {/* Comparison Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Ground Truth Box */}
          <div className="rounded-2xl bg-[#FAF8F3] p-5 border border-[#E5E1D8]">
            <div className="flex items-center justify-between text-xs font-medium text-[#7A7870] mb-2">
              <span>Ground Truth Source Evidence</span>
              <span className="font-mono text-[10px]">RAGTruth doc_4918</span>
            </div>
            <p className="text-sm font-serif italic text-[#383631] leading-relaxed">
              "{current.sourceQuote}"
            </p>
            <div className="mt-4 pt-3 border-t border-[#E8E4DA] text-xs text-[#5F5D56]">
              Verified Year: <span className="font-semibold text-[#0C0C12]">1945</span>
            </div>
          </div>

          {/* Candidate Assertion Box */}
          <div className="rounded-2xl bg-white p-5 border border-[#E5E1D8] shadow-sm">
            <div className="flex items-center justify-between text-xs font-medium text-[#7A7870] mb-2">
              <span>Perturbed Assertion</span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                current.evasionDetected ? 'bg-[#FEE2E2] text-[#991B1B]' : 'bg-[#E8F8D6] text-[#2F6B12]'
              }`}>
                {current.evasionDetected ? 'Detector Compromised' : 'Detector Robust'}
              </span>
            </div>
            <p className="text-sm font-medium text-[#0C0C12] leading-relaxed">
              "{current.text}"
            </p>
            <div className="mt-4 pt-3 border-t border-[#F2EFE8] flex items-center justify-between text-xs">
              <span className="text-[#7A7870]">Claimed Year: <strong className="text-[#DC2626] font-mono">2022</strong> (False)</span>
              <span className="font-mono font-semibold text-[#0C0C12]">
                Verdict: {current.verdict}
              </span>
            </div>
          </div>
        </div>

        {/* Softmax Probability Distribution & Academic Explanation */}
        <div className="rounded-2xl bg-[#FAF8F3] p-5 border border-[#E5E1D8]">
          <div className="flex items-center justify-between text-xs text-[#7A7870] font-medium mb-3">
            <span>DeBERTa-v3 Softmax Shift</span>
            <span className="font-mono tabular-nums">Contradiction Confidence: {(current.confidence * 100).toFixed(1)}%</span>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#15803D] font-medium">Entailment</span>
                <span className="font-mono text-[#15803D] tabular-nums">{(current.nli.entailment * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 w-full bg-[#E8E4DA] rounded-full overflow-hidden">
                <div className="h-full bg-[#15803D] rounded-full" style={{ width: `${current.nli.entailment * 100}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#DC2626] font-medium">Contradiction</span>
                <span className="font-mono text-[#DC2626] tabular-nums">{(current.nli.contradiction * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 w-full bg-[#E8E4DA] rounded-full overflow-hidden">
                <div className="h-full bg-[#DC2626] rounded-full" style={{ width: `${current.nli.contradiction * 100}%` }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#7A7870] font-medium">Neutral</span>
                <span className="font-mono text-[#7A7870] tabular-nums">{(current.nli.neutral * 100).toFixed(1)}%</span>
              </div>
              <div className="h-2 w-full bg-[#E8E4DA] rounded-full overflow-hidden">
                <div className="h-full bg-[#7A7870] rounded-full" style={{ width: `${current.nli.neutral * 100}%` }} />
              </div>
            </div>
          </div>

          <p className="text-xs text-[#47453F] leading-relaxed">
            <strong className="text-[#0C0C12]">Novelty Finding: </strong>
            {current.analysis}
          </p>
        </div>
      </section>

      {/* RAGTruth Benchmark Performance Table */}
      <section className="rx-card p-6 md:p-7">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-5 border-b border-[#F2EFE8]">
          <div>
            <h3 className="font-serif text-lg font-semibold text-[#0C0C12]">
              Empirical Robustness Benchmark Results
            </h3>
            <p className="text-xs text-[#7A7870] mt-0.5">
              Empirical evaluation across real human-labeled hallucinations from the RAGTruth ACL 2024 corpus
            </p>
          </div>
          <span className="text-xs font-mono text-[#059669] bg-[#E8F8D6] px-2.5 py-1 rounded-full font-medium">Pilot: 50 Real Samples</span>
        </div>

        <div className="overflow-x-auto mt-2">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="text-[11px] font-medium text-[#8C887E] uppercase tracking-wider border-b border-[#F7F5F0]">
                <th className="py-3 px-3">Evaluation Vector</th>
                <th className="py-3 px-3">Methodology / Reference</th>
                <th className="py-3 px-3">Baseline Detection</th>
                <th className="py-3 px-3">Post-Attack Detection</th>
                <th className="py-3 px-3 text-right">Evasion Rate (ESR)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F9F7F2] text-xs">
              <tr className="hover:bg-[#FAF9F5] transition-colors">
                <td className="py-3 px-3 font-medium text-[#0C0C12]">Synonym Substitution</td>
                <td className="py-3 px-3 text-[#5F5D56]">TextAttack WordSwapWordNet (EMNLP 2020)</td>
                <td className="py-3 px-3 text-[#059669] font-medium">90.0%</td>
                <td className="py-3 px-3 text-[#059669] font-medium">90.0%</td>
                <td className="py-3 px-3 text-right font-serif text-sm font-semibold text-[#059669]">0.0% (Invariance Holds)</td>
              </tr>
              <tr className="hover:bg-[#FAF9F5] transition-colors">
                <td className="py-3 px-3 font-medium text-[#0C0C12]">Epistemic Hedging</td>
                <td className="py-3 px-3 text-[#5F5D56]">Modal Insertion (CoNLL-2010 Taxonomy)</td>
                <td className="py-3 px-3 text-[#059669] font-medium">90.0%</td>
                <td className="py-3 px-3 text-[#059669] font-medium">98.0%</td>
                <td className="py-3 px-3 text-right font-serif text-sm font-semibold text-[#059669]">0.0% (Blocked as Ungrounded)</td>
              </tr>
              <tr className="hover:bg-[#FAF9F5] transition-colors">
                <td className="py-3 px-3 font-medium text-[#0C0C12]">Syntactic Paraphrase</td>
                <td className="py-3 px-3 text-[#5F5D56]">Voice & Inversion (CheckList ACL 2020)</td>
                <td className="py-3 px-3 text-[#059669] font-medium">90.0%</td>
                <td className="py-3 px-3 text-[#059669] font-medium">100.0%</td>
                <td className="py-3 px-3 text-right font-serif text-sm font-semibold text-[#059669]">0.0% (100% Caught)</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

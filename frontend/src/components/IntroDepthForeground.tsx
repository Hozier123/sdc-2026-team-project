import { memo, type RefObject } from "react";
import { useIntroPhone } from "./useIntroPhone";
import type { IntroChapter } from "../lib/intro-depth";
import DepthText from "./reactbits/DepthText";

const stories = [
  { title: "AI reads.", body: "English, Malay and Chinese messages become one order draft. Unclear specifications go back to the customer.", side: "left" },
  { title: "Rules check.", body: "Catalogue, customer tier prices and stock are checked. A quoted price is never applied automatically.", side: "right" },
  { title: "People approve.", body: "Routine orders go to the clerk. Discounts, large orders and credit notices go to the owner. Stock limits always apply.", side: "left" },
] as const;

const OpeningTitle = memo(function OpeningTitle({ active, phone }: { active: boolean; phone: boolean }) {
  // The mobile title stays mounted across chapters instead of rebuilding depth layers on reverse scroll.
  return phone || active ? <DepthText
    text="KiraOrder" layers={phone ? 3 : 8} depth={phone ? 1.8 : 0.85} tilt={3} fontWeight={400}
    faceColor="var(--intro-ink)" depthColor="var(--intro-depth-ink)" fontSize="inherit"
    autoOrbit={false} pointerTracking={!phone} shadow={false} intro={false} hoverPush={0}
    className="intro-depth-title"
  /> : <span>KiraOrder</span>;
});

export function IntroDepthForeground({ foreground, opening, notes, closing, chapter, paused, reduced }: {
  foreground: RefObject<HTMLDivElement | null>;
  opening: RefObject<HTMLElement | null>;
  notes: RefObject<(HTMLElement | null)[]>;
  closing: RefObject<HTMLDivElement | null>;
  chapter: IntroChapter;
  paused: boolean;
  reduced: boolean;
}) {
  const phone = useIntroPhone();
  return <div ref={foreground} className="intro-depth-foreground" data-depth-layer="foreground">
    <div className="intro-reading-scrim" aria-hidden="true" />
    <div className="intro-reading-scrim intro-reading-scrim-reverse" aria-hidden="true" />
    <div className="intro-closing-scrim" aria-hidden="true" />
    <div className="intro-depth-shade" data-intro-story-shade="" aria-hidden="true" />
    <section ref={opening} className="intro-opening intro-reading-plane" aria-label="KiraOrder">
      <h1>
        <OpeningTitle phone={phone} active={phone || (chapter === "welcome" && !paused && !reduced)} />
      </h1>
      <p>From a WhatsApp message to a checked delivery order.</p>
    </section>
    {stories.map((story, index) => <section
      key={story.title}
      ref={element => { notes.current[index] = element; }}
      className="intro-chapter intro-reading-plane"
      data-side={story.side}
      data-intro-step={index}
      aria-label={story.title}
    >
      <h2>{story.title}</h2>
      <p>{story.body}</p>
    </section>)}
    <div ref={closing} className="intro-depth-close intro-reading-plane">
      <h2>Every order,<br />in the right hands.</h2>
      <div className="intro-close-action-slot" data-intro-entry-slot="" aria-hidden="true" />
    </div>
  </div>;
}

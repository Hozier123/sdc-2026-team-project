import type { RefObject } from "react";
import type { IntroChapter } from "../lib/intro-depth";
import DepthText from "./reactbits/DepthText";

const stories = [
  { title: "AI reads.", body: "English, Malay and Chinese messages become one order draft. Unclear specifications go back to the customer.", side: "left" },
  { title: "Rules check.", body: "Catalogue, customer tier prices and stock are checked. A quoted price is never applied automatically.", side: "right" },
  { title: "People approve.", body: "Routine orders go to the clerk. Discounts, large orders and credit notices go to the owner. Stock limits always apply.", side: "left" },
] as const;

export function IntroDepthForeground({ foreground, opening, notes, closing, chapter, paused, reduced }: {
  foreground: RefObject<HTMLDivElement | null>;
  opening: RefObject<HTMLElement | null>;
  notes: RefObject<(HTMLElement | null)[]>;
  closing: RefObject<HTMLDivElement | null>;
  chapter: IntroChapter;
  paused: boolean;
  reduced: boolean;
}) {
  return <div ref={foreground} className="intro-depth-foreground" data-depth-layer="foreground">
    <div className="intro-reading-scrim" aria-hidden="true" />
    <div className="intro-depth-shade" data-intro-story-shade="" aria-hidden="true" />
    <section ref={opening} className="intro-opening intro-reading-plane" aria-label="KiraOrder">
      <h1>
        {chapter === "welcome" && !paused && !reduced ? <DepthText
          text="KiraOrder" layers={8} depth={0.85} tilt={3} fontWeight={400}
          faceColor="#e2ebe9" depthColor="#88ab9b" fontSize="inherit"
          autoOrbit={false} shadow={false} intro={false} hoverPush={0}
          className="intro-depth-title"
        /> : <span>KiraOrder</span>}
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

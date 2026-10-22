import { useEffect, useRef } from "react";

/** Alternate two decoders so the opening frames blend over the ending frames. */
export function SeamlessBackdrop({
  src,
  poster,
  paused,
}: {
  src: string;
  poster: string;
  paused: boolean;
}) {
  const videos = useRef<(HTMLVideoElement | null)[]>([]);
  const cycle = useRef<{ active: number; incoming: number | null }>({
    active: 0,
    incoming: null,
  });

  useEffect(() => {
    const layers = videos.current;
    layers.forEach((video) => {
      if (video) video.playbackRate = 1.2;
    });
    if (paused) {
      layers.forEach((video) => video?.pause());
      return;
    }
    let frame = 0;
    let disposed = false;
    const play = (video: HTMLVideoElement | null) => {
      if (video)
        void video.play().catch(() => {
          /* Keep the current frame or poster. */
        });
    };
    play(layers[cycle.current.active]);
    if (cycle.current.incoming !== null) play(layers[cycle.current.incoming]);

    const tick = () => {
      if (disposed) return;
      const state = cycle.current;
      const current = layers[state.active];
      if (
        current &&
        Number.isFinite(current.duration) &&
        current.duration > 0
      ) {
        const overlap = Math.min(1.6, current.duration / 3);
        const nextIndex = 1 - state.active;
        const next = layers[nextIndex];
        if (
          state.incoming === null &&
          current.currentTime >= current.duration - overlap &&
          next &&
          next.readyState >= 2
        ) {
          state.incoming = nextIndex;
          next.style.zIndex = "2";
          current.style.zIndex = "1";
          play(next);
        }
        if (state.incoming !== null) {
          const incoming = layers[state.incoming]!;
          // The incoming media clock holds the blend still while buffering.
          const progress = Math.min(1, incoming.currentTime / overlap);
          const smooth = progress * progress * (3 - 2 * progress);
          incoming.style.opacity = String(smooth);
          if (progress >= 1) {
            current.pause();
            current.style.opacity = "0";
            current.style.zIndex = "0";
            current.currentTime = 0;
            incoming.style.zIndex = "1";
            state.active = state.incoming;
            state.incoming = null;
          }
        }
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      layers.forEach((video) => video?.pause());
    };
  }, [paused, src]);

  return (
    <div className="nebula-backdrop" data-paused={paused} aria-hidden="true">
      <div className="nebula-video-drift">
        {[0, 1].map((layer) => (
          <video
            key={layer}
            ref={(video) => {
              videos.current[layer] = video;
            }}
            src={src}
            poster={poster}
            muted
            autoPlay={!paused && layer === 0}
            playsInline
            preload="auto"
            disablePictureInPicture
            className="nebula-video-layer"
            style={{
              opacity: layer === 0 ? 1 : 0,
              zIndex: layer === 0 ? 1 : 0,
            }}
          />
        ))}
      </div>
      <div className="nebula-haze nebula-haze-mint" />
      <div className="nebula-haze nebula-haze-blue" />
    </div>
  );
}

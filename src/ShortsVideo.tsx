import React from "react";
import {
  AbsoluteFill,
  Audio,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import scriptData from "../public/assets/script.json";

export const ShortsVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const words: string[] = (scriptData as { words?: string[] }).words || ["Hola"];
  const totalWords = Math.max(words.length, 1);
  const voiceOffsetFrames = Math.round(fps * 1);
  const usableFrames = Math.max(durationInFrames * 0.92, totalWords);
  const framesPerWord = usableFrames / totalWords;
  const activeFrame = Math.max(0, frame - voiceOffsetFrames);
const activeIndex = Math.min(
  Math.floor(activeFrame / framesPerWord),
  totalWords - 1
);

  const groupSize = 4;
  const currentGroupIndex = Math.floor(activeIndex / groupSize);
  const startWord = currentGroupIndex * groupSize;
  const visibleWords = words.slice(startWord, startWord + groupSize);

  const wordLocalFrame = activeFrame - activeIndex * framesPerWord;
  const jumpOffset =
    wordLocalFrame >= 0 && wordLocalFrame < 6
      ? -Math.sin((wordLocalFrame / 6) * Math.PI) * 14
      : 0;

  const currentTimeSec = (frame / fps).toFixed(1);

  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      <OffthreadVideo
        src={staticFile("assets/background.mp4")}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      />

      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0.15), rgba(0,0,0,0.45))",
        }}
      />

      <Audio src={staticFile("assets/voiceover.mp3")} />

      <div
        style={{
          position: "absolute",
          bottom: "24%",
          left: "6%",
          right: "6%",
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "14px",
          textAlign: "center",
        }}
      >
        {visibleWords.map((word, idx) => {
          const globalIdx = startWord + idx;
          const isActive = globalIdx === activeIndex;

          return (
            <span
              key={`${globalIdx}-${word}`}
              style={{
                fontFamily: "Arial, Helvetica, sans-serif",
                fontSize: "64px",
                fontWeight: 900,
                textTransform: "uppercase",
                color: isActive ? "#FFD400" : "#FFFFFF",
                WebkitTextStroke: "3px #000000",
                textShadow: "0px 6px 16px rgba(0,0,0,0.85)",
                transform: isActive
                  ? `translateY(${jumpOffset}px) scale(1.12)`
                  : "translateY(0px) scale(1)",
                transition: "transform 0.08s ease-out",
                display: "inline-block",
              }}
            >
              {word}
            </span>
          );
        })}
      </div>

      <div
        style={{
          position: "absolute",
          bottom: "4%",
          width: "100%",
          textAlign: "center",
          color: "rgba(255,255,255,0.5)",
          fontSize: "20px",
          fontFamily: "monospace",
        }}
      >
        {currentTimeSec}s
      </div>
    </AbsoluteFill>
  );
};
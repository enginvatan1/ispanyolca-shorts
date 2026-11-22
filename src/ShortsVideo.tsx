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
 const subtitleOffsetSec = 0.3;
  const currentSec = Math.max(0, frame / fps + subtitleOffsetSec);

  const wordTimings = (scriptData as { wordTimings?: { start: number }[] }).wordTimings;

  let activeIndex = 0;
  if (Array.isArray(wordTimings) && wordTimings.length > 0) {
    for (let i = 0; i < wordTimings.length; i++) {
      if (currentSec >= wordTimings[i].start) {
        activeIndex = i;
      }
    }
  } else {
    const estDurationSec =
      typeof (scriptData as { audioDurationSec?: number }).audioDurationSec === "number" &&
      (scriptData as { audioDurationSec?: number }).audioDurationSec! > 0
        ? (scriptData as { audioDurationSec?: number }).audioDurationSec!
        : durationInFrames / fps;
    const secPerWord = estDurationSec / totalWords;
    activeIndex = Math.min(Math.floor(currentSec / secPerWord), totalWords - 1);
  }

  const groupSize = 4;
  const currentGroupIndex = Math.floor(activeIndex / groupSize);
  const startWord = currentGroupIndex * groupSize;
  const visibleWords = words.slice(startWord, startWord + groupSize);

  const wordLocalFrame = currentSec * fps - activeIndex * 8;
    wordLocalFrame >= 0 && wordLocalFrame < 6
      ? -Math.sin((wordLocalFrame / 6) * Math.PI) * 14
      : 0;
const jumpOffset =
  wordLocalFrame >= 0 && wordLocalFrame < 6
    ? -Math.sin((wordLocalFrame / 6) * Math.PI) * 14
    : 0;
  const currentTimeSec = (frame / fps).toFixed(1);
const backgrounds =
    (scriptData as { backgrounds?: string[] }).backgrounds &&
    (scriptData as { backgrounds?: string[] }).backgrounds!.length > 0
      ? (scriptData as { backgrounds?: string[] }).backgrounds!
      : ["assets/background_1.mp4"];

  const segmentLength = Math.max(1, Math.ceil(durationInFrames / backgrounds.length));
  const bgIndex = Math.min(Math.floor(frame / segmentLength), backgrounds.length - 1);
  return (
    <AbsoluteFill style={{ backgroundColor: "#000000" }}>
      <OffthreadVideo
        key={backgrounds[bgIndex]}
        src={staticFile(backgrounds[bgIndex])}
        startFrom={0}
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
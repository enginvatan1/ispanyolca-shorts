import React from "react";
import { Composition } from "remotion";
import { ShortsVideo } from "./ShortsVideo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="ShortsVideo"
        component={ShortsVideo}
        durationInFrames={30 * 40}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
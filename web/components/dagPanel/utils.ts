import { REDUCED_MOTION_QUERY, SCREEN_ENTRANCE_MS } from '@/theme/constants';

const SLIDE_FROM_LEFT_KEYFRAMES: Keyframe[] = [
  { transform: 'translateX(-100%)' },
  { transform: 'none' },
];

const SLIDE_FROM_LEFT_TIMING: KeyframeAnimationOptions = {
  duration: SCREEN_ENTRANCE_MS,
  easing: 'ease-out',
};

/**
 * Slides an element in from the left edge of the screen.
 */
export const slideInFromLeft = (element: HTMLElement): void => {
  const reducedMotionQueryList = window.matchMedia(REDUCED_MOTION_QUERY);

  if (reducedMotionQueryList.matches) {
    return;
  }

  element.animate(SLIDE_FROM_LEFT_KEYFRAMES, SLIDE_FROM_LEFT_TIMING);
};

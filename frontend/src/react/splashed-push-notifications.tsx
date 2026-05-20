import React, { useImperativeHandle, forwardRef, useRef, useEffect } from 'react';

export type NotificationType = 'help' | 'success' | 'warning' | 'error';

export interface SplashedPushNotificationsHandle {
  createNotification: (type: NotificationType, title: string, content: string) => void;
  createRtlNotification: (type: NotificationType, title: string, content: string) => void;
}

export interface SplashedPushNotificationsProps {
  timerColor?: string;
  timerBgColor?: string;
  /** ms a toast stays on screen before auto-dismiss (default 8000) */
  durationMs?: number;
}

const ICON_SVGS: Record<NotificationType, string> = {
  success: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check-check-icon lucide-check-check"><path d="M18 6 7 17l-5-5"/><path d="m22 10-7.5 7.5L13 16"/></svg>`,
  help: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-message-circle-question-icon lucide-message-circle-question"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/></svg>`,
  warning: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-zap-icon lucide-zap"><path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/></svg>`,
  error: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-shield-x-icon lucide-shield-x"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m14.5 9.5-5 5"/><path d="m9.5 9.5 5 5"/></svg>`,
};

const CLOSE_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-x-icon lucide-x"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>`;

export const SplashedPushNotifications = forwardRef<SplashedPushNotificationsHandle, SplashedPushNotificationsProps>(
  ({ timerColor, timerBgColor, durationMs }, ref) => {
    const DURATION = Math.max(2000, durationMs ?? 8000);
    const notificationContainerRef = useRef<HTMLDivElement | null>(null);
    const rtlNotificationContainerRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
      if (document.getElementById('splashed-toast-css')) return;
      const style = document.createElement('style');
      style.id = 'splashed-toast-css';
      // Tuned to match the Nifraim cream + warm-orange palette. Smaller
      // type scale and softer fills than the upstream component default.
      style.innerHTML = `
        .notificationContainer { display: flex; flex-direction: column; align-items: flex-end; position: fixed; bottom: 18px; right: 18px; max-width: 320px; gap: 8px; z-index: 999999; font-family: 'Heebo', sans-serif; }
        .rtlNotifications { left: 18px; right: auto; transform: scale(-1, 1); align-items: flex-end; }
        .toast {
          color: var(--toast-fg, #1A1410);
          padding: 0.7rem 0.95rem 0.9rem 3.5rem;
          text-align: left;
          position: relative;
          font-weight: 500;
          margin: 1.1rem 0 0;
          opacity: 1;
          overflow: visible;
          border-radius: 0.7rem;
          background: var(--toast-bg, #FFFBF4);
          border: 1px solid var(--toast-border, #EADFCC);
          box-shadow: 0 10px 28px rgba(26, 20, 16, 0.10), 0 2px 6px rgba(26, 20, 16, 0.06);
          min-width: 240px;
        }
        .timer { position: absolute; bottom: 0; left: 10%; right: 10%; width: 80%; height: 3px; background: var(--splashed-toast-timer-bg, rgba(26,20,16,0.08)); border-radius: 2px; overflow: hidden; }
        .timerLeft, .timerRight { position: absolute; top: 0; height: 100%; left: 0; background-color: var(--splashed-toast-timer, var(--clr, #F57C00)); }
        /* Splash decoration — same radial-gradient artwork, scaled down. */
        .toast:before {
          content: "";
          position: absolute;
          width: 3.8rem;
          height: 4.2rem;
          --drop: radial-gradient(circle at 64% 51%, var(--clr) 0.35rem, #fff0 calc(0.35rem + 1px)),
                  radial-gradient(circle at 100% 100%, #fff0 0.65rem, var(--clr) calc(0.65rem + 1px) 0.9rem, #fff0 calc(0.9rem + 1px) 100%),
                  radial-gradient(circle at 0% 0%, #fff0 0.65rem, var(--clr) calc(0.65rem + 1px) 0.9rem, #fff0 calc(0.9rem + 1px) 100%),
                  radial-gradient(circle at 0% 120%, var(--clr) 2.6rem, #fff0 calc(2.6rem + 1px));
          background: radial-gradient(circle at 22% 2.6rem, var(--clr) 0.55rem, #fff0 calc(0.55rem + 1px)),
                      radial-gradient(circle at 95% 1.3rem, var(--clr) 0.06rem, #fff0 calc(0.06rem + 1px)),
                      radial-gradient(circle at 80% 1.6rem, var(--clr) 0.14rem, #fff0 calc(0.14rem + 1px)),
                      radial-gradient(circle at 80% 75%, var(--clr) 0.25rem, #fff0 calc(0.25rem + 1px)),
                      radial-gradient(circle at 43% 1.6rem, var(--clr) 0.06rem, #fff0 calc(0.06rem + 1px)),
                      radial-gradient(circle at 40% 0.7rem, var(--clr) 0.09rem, #fff0 calc(0.09rem + 1px)),
                      radial-gradient(circle at 20% 1.1rem, var(--clr) 0.18rem, #fff0 calc(0.18rem + 1px)),
                      var(--drop),
                      var(--toast-splash, rgba(245, 124, 0, 0.08));
          background-repeat: no-repeat;
          background-size: 100% 100%, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 1.15rem 1.15rem, 1.15rem 1.15rem, 100% 100%, 100% 100%;
          background-position: 0 0, 0 0, 0 0, 0 0, 0 0, 0 0, 0 0, 0 0, calc(100% - 1.2rem) 2rem, calc(100% - 1.2rem) 2.05rem, 0 0, 0 0;
          bottom: 0rem;
          left: 0rem;
          z-index: 0;
          border-radius: 0.7rem 0 0 0.7rem;
          opacity: 0.85;
        }
        .toast:after {
          content: "";
          position: absolute;
          width: 2.4rem;
          height: 2.4rem;
          background: var(--clr);
          top: -1.2rem;
          left: 1.1rem;
          border-radius: 2rem;
          display: flex;
          align-items: center;
          justify-content: center;
          box-sizing: border-box;
          box-shadow: 0 4px 10px rgba(0, 0, 0, 0.18);
        }
        .toast h3 { font-size: 0.95rem; margin: 0; line-height: 1.2rem; font-weight: 800; position: relative; color: var(--toast-title, #1A1410); }
        .toast p { position: relative; font-size: 0.78rem; line-height: 1.15rem; z-index: 1; margin: 0.22rem 0 0; font-weight: 500; color: var(--toast-body, #4A4035); }
        /* Palette — warm/cream backgrounds with the type accent reserved for the splash dot + left edge */
        .toast.success { --clr: #16A34A; --toast-splash: rgba(22, 163, 74, 0.10); border-inline-start: 3px solid #16A34A; }
        .toast.help    { --clr: #F57C00; --toast-splash: rgba(245, 124, 0, 0.10); border-inline-start: 3px solid #F57C00; }
        .toast.warning { --clr: #D97706; --toast-splash: rgba(217, 119, 6, 0.10); border-inline-start: 3px solid #D97706; }
        .toast.error   { --clr: #DC2626; --toast-splash: rgba(220, 38, 38, 0.10); border-inline-start: 3px solid #DC2626; }
        .closeButton {
          position: absolute;
          top: 0.3rem;
          right: 0.3rem;
          height: 22px;
          width: 22px;
          cursor: pointer;
          border-radius: 0.3rem;
          background: transparent;
          border: 0;
          color: rgba(26, 20, 16, 0.45);
          font-size: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 0;
          transition: background 0.15s, color 0.15s;
        }
        .closeButton:hover { background: rgba(26, 20, 16, 0.06); color: #1A1410; }
        .closeButton svg { width: 14px; height: 14px; }
        .toast .icon-center {
          position: absolute;
          width: 2.4rem;
          height: 2.4rem;
          top: -1.2rem;
          left: 1.1rem;
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 2;
          pointer-events: none;
          color: #fff;
        }
        .toast .icon-center svg { width: 1.05rem; height: 1.05rem; }
        @keyframes slideInWithBounce {
          0%   { transform: translateY(40%) scale(0.92); opacity: 0; }
          70%  { transform: translateY(-4%)  scale(1.02); opacity: 1; }
          100% { transform: translateY(0)    scale(1);    opacity: 1; }
        }
        @keyframes slideOutWithBounce {
          0%   { transform: translateY(0)    scale(1);    opacity: 1; }
          100% { transform: translateY(20%)  scale(0.95); opacity: 0; }
        }
      `;
      document.head.appendChild(style);
    }, []);

    useEffect(() => {
      const setVars = (el: HTMLDivElement | null) => {
        if (!el) return;
        if (timerColor) el.style.setProperty('--splashed-toast-timer', timerColor);
        else el.style.removeProperty('--splashed-toast-timer');
        if (timerBgColor) el.style.setProperty('--splashed-toast-timer-bg', timerBgColor);
        else el.style.removeProperty('--splashed-toast-timer-bg');
      };
      setVars(notificationContainerRef.current);
      setVars(rtlNotificationContainerRef.current);
    }, [timerColor, timerBgColor]);

    const setTimerAnimation = (timerLeft: HTMLElement, timerRight: HTMLElement, duration: number, uniqueId: number) => {
      const stylesheet = document.createElement("style");
      stylesheet.type = "text/css";
      stylesheet.innerHTML = `
        @keyframes timerShrink-${uniqueId} {
          from { width: 100%; }
          to { width: 0; }
        }
      `;
      document.head.appendChild(stylesheet);
      timerLeft.style.animation = `timerShrink-${uniqueId} ${duration}ms linear forwards`;
      timerRight.style.animation = `timerShrink-${uniqueId} ${duration}ms linear forwards`;
    };

    const removeNotification = (notif: HTMLElement) => {
      notif.style.animation = 'slideOutWithBounce 0.6s ease forwards';
      setTimeout(() => { notif.remove(); }, 600);
    };

    const createNotification = (type: NotificationType, notificationTitle: string, notificationContent: string) => {
      if (notificationContainerRef.current) {
        const notif = document.createElement('div');
        notif.classList.add('toast', type);

        const iconDiv = document.createElement('div');
        iconDiv.className = 'icon-center';
        iconDiv.innerHTML = ICON_SVGS[type];

        const title = document.createElement('h3');
        title.textContent = notificationTitle;
        title.style.margin = '0';

        const content = document.createElement('p');
        content.textContent = notificationContent;
        content.style.margin = '0.25rem 0';

        const timerContainer = document.createElement('div');
        timerContainer.classList.add('timer');

        const closeButton = document.createElement('button');
        closeButton.classList.add('closeButton');
        closeButton.innerHTML = CLOSE_SVG;
        closeButton.onclick = () => { removeNotification(notif); };

        notif.appendChild(iconDiv);
        notif.appendChild(closeButton);
        notif.appendChild(title);
        notif.appendChild(content);
        notif.appendChild(timerContainer);

        const timerLeft = document.createElement('div');
        timerLeft.classList.add('timerLeft');
        const timerRight = document.createElement('div');
        timerRight.classList.add('timerRight');
        timerContainer.appendChild(timerRight);
        timerContainer.appendChild(timerLeft);

        notificationContainerRef.current.appendChild(notif);
        notif.style.animation = 'slideInWithBounce 0.6s ease forwards';

        const duration = DURATION;
        const uniqueId = Date.now();
        setTimerAnimation(timerLeft, timerRight, duration, uniqueId);

        let timeoutId: ReturnType<typeof setTimeout>;
        timeoutId = setTimeout(() => removeNotification(notif), duration);
        let remainingTime = duration;

        notif.addEventListener("mouseenter", () => {
          clearTimeout(timeoutId);
          const computedWidth = parseFloat(getComputedStyle(timerLeft).width);
          const totalWidth = parseFloat(getComputedStyle(timerContainer).width);
          const elapsedTime = (computedWidth / totalWidth) * duration;
          remainingTime = duration - elapsedTime;
          (timerLeft as HTMLElement).style.animationPlayState = "paused";
          (timerRight as HTMLElement).style.animationPlayState = "paused";
        });

        notif.addEventListener("mouseleave", () => {
          if (remainingTime > 0) {
            setTimerAnimation(timerLeft, timerRight, duration, uniqueId);
            timeoutId = setTimeout(() => removeNotification(notif), duration - remainingTime);
            (timerLeft as HTMLElement).style.animationPlayState = "running";
            (timerRight as HTMLElement).style.animationPlayState = "running";
          }
        });
      }
    };

    const createRtlNotification = (type: NotificationType, notificationTitle: string, notificationContent: string) => {
      if (rtlNotificationContainerRef.current) {
        const notif = document.createElement('div');
        notif.classList.add('toast', type, 'rtl');

        const iconDiv = document.createElement('div');
        iconDiv.className = 'icon-center';
        iconDiv.innerHTML = ICON_SVGS[type];

        const title = document.createElement('h3');
        title.textContent = notificationTitle;
        title.style.margin = '0';
        title.style.transform = 'scale(-1, 1)';
        title.style.textAlign = 'right';
        title.style.direction = 'rtl';

        const content = document.createElement('p');
        content.textContent = notificationContent;
        content.style.margin = '0.25rem 0';
        content.style.transform = 'scale(-1, 1)';
        content.style.textAlign = 'right';
        content.style.direction = 'rtl';

        const timerContainer = document.createElement('div');
        timerContainer.classList.add('timer');

        const closeButton = document.createElement('button');
        closeButton.classList.add('closeButton');
        closeButton.innerHTML = CLOSE_SVG;
        closeButton.onclick = () => { removeNotification(notif); };

        notif.appendChild(iconDiv);
        notif.appendChild(closeButton);
        notif.appendChild(title);
        notif.appendChild(content);
        notif.appendChild(timerContainer);

        const timerLeft = document.createElement('div');
        timerLeft.classList.add('timerLeft');
        const timerRight = document.createElement('div');
        timerRight.classList.add('timerRight');
        timerContainer.appendChild(timerRight);
        timerContainer.appendChild(timerLeft);

        rtlNotificationContainerRef.current.appendChild(notif);
        notif.style.animation = 'slideInWithBounce 0.6s ease forwards';

        const duration = DURATION;
        const uniqueId = Date.now();
        setTimerAnimation(timerLeft, timerRight, duration, uniqueId);

        let timeoutId: ReturnType<typeof setTimeout>;
        timeoutId = setTimeout(() => removeNotification(notif), duration);
        let remainingTime = duration;

        notif.addEventListener("mouseenter", () => {
          clearTimeout(timeoutId);
          const computedWidth = parseFloat(getComputedStyle(timerLeft).width);
          const totalWidth = parseFloat(getComputedStyle(timerContainer).width);
          const elapsedTime = (computedWidth / totalWidth) * duration;
          remainingTime = duration - elapsedTime;
          (timerLeft as HTMLElement).style.animationPlayState = "paused";
          (timerRight as HTMLElement).style.animationPlayState = "paused";
        });

        notif.addEventListener("mouseleave", () => {
          if (remainingTime > 0) {
            setTimerAnimation(timerLeft, timerRight, duration, uniqueId);
            timeoutId = setTimeout(() => removeNotification(notif), duration - remainingTime);
            (timerLeft as HTMLElement).style.animationPlayState = "running";
            (timerRight as HTMLElement).style.animationPlayState = "running";
          }
        });
      }
    };

    useImperativeHandle(ref, () => ({
      createNotification,
      createRtlNotification,
    }));

    return (
      <>
        <div ref={notificationContainerRef} className="notificationContainer"></div>
        <div ref={rtlNotificationContainerRef} className="notificationContainer rtlNotifications"></div>
      </>
    );
  }
);

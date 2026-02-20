import { SvgIcon, SvgIconProps } from "@mui/material";

const TurnstileIcon = (props: SvgIconProps) => (
    <SvgIcon {...props} viewBox="0 0 24 24">
        {/* Main pillar body */}
        <path d="M2 2 L8 2 L8 22 L5 22 L5 20 L2 22 L2 2 Z" fill="currentColor" />

        {/* Wider base */}
        <path d="M1 19 L9 19 L9 22 L8 22 L8 20 L2 20 L1 22 L1 19 Z" fill="currentColor" />
        <path d="M1 22 L9 22 L9 22.5 L1 22.5 Z" fill="currentColor" />

        {/* Screen/display on pillar (white cutout) */}
        <rect x="3" y="3.5" width="3.5" height="2" rx="0.3" fill="none" stroke="white" strokeWidth="0.7" />

        {/* Half-circle pivot joint */}
        <path d="M8 7 A4 4 0 0 1 8 15" fill="white" stroke="currentColor" strokeWidth="0.3" />

        {/* Arm 1 - going up-right (nearly horizontal) */}
        <line x1="10" y1="8" x2="22" y2="4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />

        {/* Arm 2 - going down vertically */}
        <line x1="9" y1="13" x2="7.5" y2="19" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />

        {/* Arm 3 - going down-right (diagonal) */}
        <line x1="10" y1="12" x2="20" y2="20" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </SvgIcon>
);

export default TurnstileIcon;

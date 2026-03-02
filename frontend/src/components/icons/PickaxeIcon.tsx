import { SvgIcon, SvgIconProps } from "@mui/material";

const PickaxeIcon = (props: SvgIconProps) => (
    <SvgIcon {...props} viewBox="0 0 24 24">
        {/* Helmet top */}
        <path
            d="M4 14a8 8 0 0 1 16 0"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
        />

        {/* Front round frame */}
        <circle
            cx="12"
            cy="14"
            r="2.8"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
        />

        {/* Top center piece */}
        <path d="M10.7 5.2h2.6v4.1h-2.6z" fill="currentColor" />

        {/* Brim */}
        <path
            d="M4.2 18h15.6"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
        />
    </SvgIcon>
);

export default PickaxeIcon;

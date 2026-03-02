import { SvgIcon, SvgIconProps } from "@mui/material";

const LampIcon = (props: SvgIconProps) => (
    <SvgIcon {...props} viewBox="0 0 24 24">
        {/* Top strap */}
        <path
            d="M9.3 4.5h5.4l-.5 3.8H9.8z"
            fill="currentColor"
        />

        {/* Helmet arc */}
        <path
            d="M4 13a8 8 0 0 1 16 0"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
        />

        {/* Lamp body */}
        <circle
            cx="12"
            cy="13.2"
            r="3.1"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
        />
        <circle cx="12" cy="13.2" r="1.1" fill="currentColor" />

        {/* Brim */}
        <path
            d="M4.2 18.2h15.6"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
        />
    </SvgIcon>
);

export default LampIcon;

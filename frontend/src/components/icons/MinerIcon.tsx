import { SvgIcon, SvgIconProps } from "@mui/material";

const MinerIcon = (props: SvgIconProps) => (
    <SvgIcon {...props} viewBox="0 0 24 24">
        {/* Helmet shell */}
        <path d="M4 13a8 8 0 0 1 16 0v1H4v-1Z" fill="currentColor" />

        {/* Top cap */}
        <path d="M10 4h4l-.4 4.2h-3.2L10 4Z" fill="currentColor" />

        {/* Brim */}
        <rect x="2" y="15" width="20" height="2.6" rx="1.3" fill="currentColor" />

        {/* Center circular badge/ring */}
        <circle cx="12" cy="12.6" r="2.6" fill="none" stroke="currentColor" strokeWidth="1.8" />
    </SvgIcon>
);

export default MinerIcon;

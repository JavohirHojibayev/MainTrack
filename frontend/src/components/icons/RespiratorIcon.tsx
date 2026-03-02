import { SvgIcon, SvgIconProps } from "@mui/material";

const RespiratorIcon = (props: SvgIconProps) => (
    <SvgIcon {...props} viewBox="0 0 24 24">
        {/* side filters */}
        <circle cx="6.4" cy="12.4" r="2.7" fill="currentColor" />
        <circle cx="17.6" cy="12.4" r="2.7" fill="currentColor" />

        {/* main respirator body */}
        <rect x="7" y="8.1" width="10" height="9.2" rx="4.2" fill="currentColor" />

        {/* center valve cutout */}
        <circle cx="12" cy="12.8" r="1.5" fill="white" />
        <circle cx="12" cy="12.8" r="0.65" fill="currentColor" />

        {/* top strap */}
        <path
            d="M8.1 7.1c1.1-1.4 2.4-2 3.9-2s2.8.6 3.9 2"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
        />
    </SvgIcon>
);

export default RespiratorIcon;

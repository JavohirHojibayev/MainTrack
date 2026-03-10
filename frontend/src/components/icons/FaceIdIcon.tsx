import { SvgIcon, SvgIconProps } from "@mui/material";

const FaceIdIcon = (props: SvgIconProps) => (
    <SvgIcon {...props} viewBox="0 0 24 24">
        <path d="M4.5 5.5V4h3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M4.5 18.5V20h3" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M11.3 4H8.8v1.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M11.3 20H8.8v-1.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />

        <path d="M3.2 12h8" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
        <path d="M7.9 8.8L11.4 12L7.9 15.2" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />

        <path d="M12.4 4.6L18.8 6.6V17.4L12.4 19.4V4.6Z" fill="currentColor" />
        <circle cx="14.2" cy="12" r="0.8" fill="#ffffff" />
    </SvgIcon>
);

export default FaceIdIcon;

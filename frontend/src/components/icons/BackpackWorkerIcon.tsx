import { SvgIcon, SvgIconProps } from "@mui/material";

const BackpackWorkerIcon = (props: SvgIconProps) => (
    <SvgIcon {...props} viewBox="0 0 24 24">
        {/* backpack (behind body) */}
        <rect x="13.4" y="8.2" width="5.2" height="8.2" rx="1.4" fill="currentColor" />
        <rect x="14.3" y="9.3" width="3.4" height="1.2" rx="0.6" fill="white" />

        {/* head */}
        <circle cx="10.2" cy="6.2" r="2.2" fill="currentColor" />

        {/* neck + torso */}
        <path
            d="M7.2 10.1c0-1.2 1-2.2 2.2-2.2h1.8c1.3 0 2.4 1.1 2.4 2.4v3.8c0 .9-.7 1.6-1.6 1.6H8.8c-.9 0-1.6-.7-1.6-1.6v-4Z"
            fill="currentColor"
        />

        {/* left arm */}
        <rect x="5.6" y="10.4" width="1.6" height="4.6" rx="0.8" fill="currentColor" />

        {/* legs */}
        <rect x="8.5" y="15.2" width="1.8" height="4.8" rx="0.9" fill="currentColor" />
        <rect x="11.2" y="15.2" width="1.8" height="4.8" rx="0.9" fill="currentColor" />
    </SvgIcon>
);

export default BackpackWorkerIcon;

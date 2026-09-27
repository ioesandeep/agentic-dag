import { buttonClasses } from '@mui/material/Button';

export const FAILURE_STYLE = { flexBasis: '100%' };
export const DISABLED_BUTTON_STYLE = {
  [`&.${buttonClasses.disabled}`]: { color: 'text.secondary' },
};

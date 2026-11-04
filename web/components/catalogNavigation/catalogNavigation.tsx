'use client';

import Drawer from '@mui/material/Drawer';
import type { DrawerProps } from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Tooltip from '@mui/material/Tooltip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useTheme } from '@mui/material/styles';
import AccountTreeOutlinedIcon from '@mui/icons-material/AccountTreeOutlined';
import FolderOutlinedIcon from '@mui/icons-material/FolderOutlined';
import CodeOutlinedIcon from '@mui/icons-material/CodeOutlined';
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import MenuIcon from '@mui/icons-material/Menu';
import HubOutlinedIcon from '@mui/icons-material/HubOutlined';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';

import { LABELS } from '@/labels/en';
import { DAGS_ROUTE, PROJECTS_ROUTE, REPOSITORIES_ROUTE } from '@/utils/route';

const CATALOG_LINKS = [
  { href: DAGS_ROUTE, label: LABELS.catalogDags, icon: AccountTreeOutlinedIcon },
  { href: PROJECTS_ROUTE, label: LABELS.projectsHeading, icon: FolderOutlinedIcon },
  { href: REPOSITORIES_ROUTE, label: LABELS.repositoriesHeading, icon: CodeOutlinedIcon },
];

const EXPANDED_DRAWER_WIDTH = '15rem';
const COLLAPSED_DRAWER_WIDTH = '4.5rem';
const BRAND_STYLE = { p: 1, alignItems: 'center' };
const TITLE_STYLE = { flexGrow: 1 };
const SETTINGS_STYLE = { mt: 'auto' };
const NAVIGATION_ID = 'catalog-navigation';
const DESKTOP_QUERY_CONFIG = { defaultMatches: true };

/**
 * Links to console sections and identifies the current section.
 */
export const CatalogNavigation = () => {
  const [expandedOverride, setExpandedOverride] = useState<boolean | null>(null);
  const theme = useTheme();

  const desktopQuery = theme.breakpoints.up('md');
  const isDesktop = useMediaQuery(desktopQuery, DESKTOP_QUERY_CONFIG);
  const pathname = usePathname();

  const isExpanded = expandedOverride ?? isDesktop;
  const drawerWidth = isExpanded ? EXPANDED_DRAWER_WIDTH : COLLAPSED_DRAWER_WIDTH;
  const toggleLabel = isExpanded ? LABELS.catalogCollapse : LABELS.catalogExpand;

  const handleToggle = () => setExpandedOverride(!isExpanded);
  const handleCollapse = () => setExpandedOverride(false);
  const handleNavigate = () => {
    if (!isDesktop) {
      handleCollapse();
    }
  };

  const navigationStyle = { width: { xs: COLLAPSED_DRAWER_WIDTH, md: drawerWidth }, flexShrink: 0 };
  const paperWidth = isDesktop ? drawerWidth : EXPANDED_DRAWER_WIDTH;
  const paperStyle = { width: paperWidth, boxSizing: 'border-box', overflowX: 'hidden' };

  const drawerSlotProps: DrawerProps['slotProps'] = {
    paper: { component: 'nav', 'aria-label': LABELS.catalogNavigation, sx: paperStyle },
  };

  const labelStyle = { display: isExpanded ? 'block' : 'none' };
  const iconStyle = { minWidth: 0, mr: isExpanded ? 3 : 0 };

  const linkStyle = { minHeight: '3rem', justifyContent: isExpanded ? 'flex-start' : 'center' };
  const headerDirection = isExpanded ? 'row' : 'column';
  const ToggleIcon = isExpanded ? ChevronLeftIcon : MenuIcon;
  const drawerVariant = isDesktop ? 'permanent' : 'temporary';

  return (
    <Box sx={navigationStyle}>
      {!isDesktop && <Stack spacing={1} sx={BRAND_STYLE}>
        <HubOutlinedIcon color="primary" titleAccess={LABELS.appTitle} />
        <Tooltip title={LABELS.catalogExpand}>
          <IconButton aria-label={LABELS.catalogExpand} aria-expanded={isExpanded} onClick={handleToggle}>
            <MenuIcon />
          </IconButton>
        </Tooltip>
      </Stack>}
      <Drawer variant={drawerVariant} open={isExpanded} onClose={handleCollapse} slotProps={drawerSlotProps}>
        <Stack direction={headerDirection} spacing={1} sx={BRAND_STYLE}>
          <HubOutlinedIcon color="primary" titleAccess={LABELS.appTitle} />
          {isExpanded && <Typography variant="subtitle1" noWrap sx={TITLE_STYLE}>{LABELS.appTitle}</Typography>}
          <Tooltip title={toggleLabel}>
            <IconButton autoFocus={!isDesktop} aria-label={toggleLabel} aria-expanded={isExpanded} aria-controls={NAVIGATION_ID} onClick={handleToggle}>
              <ToggleIcon />
            </IconButton>
          </Tooltip>
        </Stack>
        <List id={NAVIGATION_ID}>
          {CATALOG_LINKS.map(({ href, label, icon: Icon }) => {
            const isCurrent = pathname === href || (pathname?.startsWith(`${href}/`) ?? false);
            const ariaCurrent = isCurrent ? 'page' : undefined;

            return (
              <ListItem key={href} disablePadding>
                <Tooltip title={label} placement="right">
                  <ListItemButton component={Link} href={href} onClick={handleNavigate} selected={isCurrent} aria-label={label} aria-current={ariaCurrent} sx={linkStyle}>
                    <ListItemIcon sx={iconStyle}><Icon /></ListItemIcon>
                    <ListItemText primary={label} sx={labelStyle} />
                  </ListItemButton>
                </Tooltip>
              </ListItem>
            );
          })}
        </List>
        <List sx={SETTINGS_STYLE}>
          <Tooltip title={LABELS.catalogSettings} placement="right">
            <ListItem disablePadding>
              <ListItemButton component="button" disabled aria-label={LABELS.catalogSettings} sx={linkStyle}>
                <ListItemIcon sx={iconStyle}><SettingsOutlinedIcon /></ListItemIcon>
                <ListItemText primary={LABELS.catalogSettings} sx={labelStyle} />
              </ListItemButton>
            </ListItem>
          </Tooltip>
        </List>
      </Drawer>
    </Box>
  );
};

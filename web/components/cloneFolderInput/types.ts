/**
 * Describes the browser's native directory selection API.
 */
export interface DirectoryPickerWindow extends Window {
  showDirectoryPicker?: () => Promise<FileSystemDirectoryHandle>;
}

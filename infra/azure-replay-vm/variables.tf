variable "subscription_id" {
  type = string
}

variable "name" {
  type    = string
  default = "r6replay"
}

variable "location" {
  type    = string
  default = "swedencentral" # A10 (NVadsA10 v5) availability; check quota with `az vm list-usage`
}

variable "vm_size" {
  description = "NV12ads_A10_v5 = 1/3 A10 (8 GB VRAM), enough for the replay viewer at 1080p."
  type        = string
  default     = "Standard_NV12ads_A10_v5"
}

variable "use_spot" {
  type    = bool
  default = true
}

variable "os_disk_gb" {
  type    = number
  default = 256
}

variable "image" {
  type = object({ publisher = string, offer = string, sku = string })
  default = {
    publisher = "MicrosoftWindowsDesktop"
    offer     = "windows-11"
    sku       = "win11-24h2-pro"
  }
}

variable "windows_license_type" {
  description = "Windows_Client if you have eligible Windows 11 licensing (multitenant rights); null otherwise."
  type        = string
  default     = "Windows_Client"
}

variable "admin_username" {
  type    = string
  default = "huus"
}

variable "admin_password" {
  type      = string
  sensitive = true
}

variable "allowed_source_cidrs" {
  description = "Your home IP(s) for RDP, e.g. [\"203.0.113.10/32\"]."
  type        = list(string)
}

variable "shutdown_time" {
  type    = string
  default = "0100"
}

variable "tags" {
  type    = map(string)
  default = { project = "r6-broadcast" }
}

terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.name}"
  location = var.location
  tags     = var.tags
}

resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-${var.name}"
  address_space       = ["10.42.0.0/24"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags
}

resource "azurerm_subnet" "snet" {
  name                 = "snet-vm"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.42.0.0/26"]
}

resource "azurerm_network_security_group" "nsg" {
  name                = "nsg-${var.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags

  security_rule {
    name                       = "rdp-from-home"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3389"
    source_address_prefixes    = var.allowed_source_cidrs
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "nsg" {
  subnet_id                 = azurerm_subnet.snet.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_public_ip" "pip" {
  name                = "pip-${var.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_network_interface" "nic" {
  name                = "nic-${var.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  tags                = var.tags

  ip_configuration {
    name                          = "ipconfig1"
    subnet_id                     = azurerm_subnet.snet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.pip.id
  }
}

resource "azurerm_windows_virtual_machine" "vm" {
  name                  = "vm-${var.name}"
  computer_name         = "r6replay"
  location              = azurerm_resource_group.rg.location
  resource_group_name   = azurerm_resource_group.rg.name
  size                  = var.vm_size
  admin_username        = var.admin_username
  admin_password        = var.admin_password
  network_interface_ids = [azurerm_network_interface.nic.id]
  license_type          = var.windows_license_type
  tags                  = var.tags

  # Spot keeps the hourly cost down; the VM is deallocated (not deleted) on eviction.
  priority        = var.use_spot ? "Spot" : "Regular"
  eviction_policy = var.use_spot ? "Deallocate" : null
  max_bid_price   = var.use_spot ? -1 : null

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = var.os_disk_gb # Siege is ~90 GB + replays + recordings
  }

  source_image_reference {
    publisher = var.image.publisher
    offer     = var.image.offer
    sku       = var.image.sku
    version   = "latest"
  }
}

# NVIDIA GRID driver for the A10 vGPU.
resource "azurerm_virtual_machine_extension" "gpu" {
  name                       = "NvidiaGpuDriverWindows"
  virtual_machine_id         = azurerm_windows_virtual_machine.vm.id
  publisher                  = "Microsoft.HpcCompute"
  type                       = "NvidiaGpuDriverWindows"
  type_handler_version       = "1.6"
  auto_upgrade_minor_version = true
  tags                       = var.tags
}

# Installs Steam, Ubisoft Connect, OBS, Python, ffmpeg and the r6cast agent.
resource "azurerm_virtual_machine_extension" "bootstrap" {
  name                 = "bootstrap"
  virtual_machine_id   = azurerm_windows_virtual_machine.vm.id
  publisher            = "Microsoft.Compute"
  type                 = "CustomScriptExtension"
  type_handler_version = "1.10"
  tags                 = var.tags

  protected_settings = jsonencode({
    commandToExecute = "powershell -ExecutionPolicy Bypass -EncodedCommand ${textencodebase64(file("${path.module}/bootstrap.ps1"), "UTF-16LE")}"
  })

  depends_on = [azurerm_virtual_machine_extension.gpu]
}

# Shut down every night so a forgotten VM doesn't keep billing.
resource "azurerm_dev_test_global_vm_shutdown_schedule" "nightly" {
  virtual_machine_id    = azurerm_windows_virtual_machine.vm.id
  location              = azurerm_resource_group.rg.location
  enabled               = true
  daily_recurrence_time = var.shutdown_time
  timezone              = "Romance Standard Time" # Copenhagen

  notification_settings {
    enabled = false
  }
}

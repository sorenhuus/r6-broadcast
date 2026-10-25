output "public_ip" {
  value = azurerm_public_ip.pip.ip_address
}

output "rdp" {
  value = "mstsc /v:${azurerm_public_ip.pip.ip_address}"
}

output "start_stop" {
  value = {
    start = "az vm start -g ${azurerm_resource_group.rg.name} -n ${azurerm_windows_virtual_machine.vm.name}"
    stop  = "az vm deallocate -g ${azurerm_resource_group.rg.name} -n ${azurerm_windows_virtual_machine.vm.name}"
  }
}

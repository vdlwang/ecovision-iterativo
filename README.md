# TCC Testes
Repositório para testes do projeto CyberReciclagem. Esse projeto é o trabalho de conclusão de curso para a Engenharia de Computação da Escola Politécnica, Universidade de São Paulo.

## branch br-wang
Branch de Victor de Lima Wang para testes pessoais, de forma a acompanhar o desenvolvimento do membro do grupo.

### Notes
Para rodar o python com PyTorch configurado para Cuda, é necessário trocar o driver da placa de vídeo de nouveau para o driver proprietário da Nvidia. Para alternar entre os dois drivers, altere linha começando com `GRUB_CMDLINE_LINUX=` do arquivo em `/etc/default/grub`:

```cmd
rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nvidia-drm.modeset=1 initcall_blacklist=simpledrm_platform_driver_init
```

Então, execute `sudo grub2-mkconfig -o /boot/grub2/grub.cfg`. fonte: `https://discussion.fedoraproject.org/t/how-to-properly-revert-from-nvidia-to-nouveau-in-fedora-37/61585`.

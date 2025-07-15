{
  perSystem =
    {
      config,
      lib,
      pkgs,
      ...
    }:
    let
      cfg = config.pre-commit;
    in
    {
      # Adapted from
      # https://github.com/cachix/git-hooks.nix/blob/dcf5072734cb576d2b0c59b2ac44f5050b5eac82/flake-module.nix#L66-L78
      devShells.default = pkgs.mkShell {
        packages = lib.flatten [
          cfg.settings.enabledPackages
          cfg.settings.package
          pkgs.uv
          pkgs.python313Full

          # Mostly just for text editor
          # pkgs.python313Packages.scrapy
          pkgs.python313Packages.beautifulsoup4
        ];

        shellHook = builtins.concatStringsSep "\n" [
          cfg.installationScript
        ];
      };
    };
}

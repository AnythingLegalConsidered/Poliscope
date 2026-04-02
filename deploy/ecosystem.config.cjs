// PM2 ecosystem config for Poliscope production
// Deploy to LXC: rsync deploy/ecosystem.config.cjs root@192.168.2.200:/opt/poliscope/
// Start: cd /opt/poliscope && pm2 startOrRestart ecosystem.config.cjs --env production

module.exports = {
  apps: [{
    name: 'poliscope',
    script: '/opt/poliscope/.output/server/index.mjs',
    cwd: '/opt/poliscope',
    instances: 1,
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'production',
      NITRO_PORT: '3000',
    },
    env_file: '/opt/poliscope/.env',
    max_memory_restart: '512M',
    log_date_format: 'YYYY-MM-DD HH:mm:ss',
  }],
}

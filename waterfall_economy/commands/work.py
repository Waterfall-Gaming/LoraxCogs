from redbot.core import Config, commands, app_commands, bank
from redbot.core.utils.chat_formatting import humanize_number

from datetime import datetime, timezone, timedelta
from random import randint

import discord
import calendar

from waterfall_economy.util.embeds import ErrorEmbed


class WorkCommand(commands.Cog):
  """The work command"""

  def __init__(self, bot):
    # super().__init__()
    self.bot = bot
    self.config = None

  @commands.group(name="work", aliases=["job"])
  @commands.guild_only()
  async def command_work(self, ctx):
    """Commands for working to get credits"""

  @command_work.command(name="list")
  async def command_work_list(self, ctx):
    """List all available jobs"""
    jobs = await self.config.JOBS()
    current_job = await self.config.member(ctx.author).job()
    global_times_worked = await self.config.member(ctx.author).job_global_times_worked()

    currency = await bank.get_currency_name(ctx.guild)
    embed = discord.Embed(title="Available Jobs")

    for job in jobs:
      embed.add_field(
        name=f"{jobs[job]['emoji']} {jobs[job]['name']} {'(Current Job)' if current_job and current_job == job else ''}",
        value=f"{jobs[job]['description']}\n"
              f"ID: `{job}`\n"
              f"Times worked required: {jobs[job]['min_times_worked']} {':heavy_check_mark:' if global_times_worked >= jobs[job]['min_times_worked'] else ':x:'}\n"
              f"Starting rate: {humanize_number(jobs[job]['tiers'][0]['rate'])} {currency}/hour",
        inline=False
      )

    await ctx.send(embed=embed)


  @command_work.command(name="info", aliases=["details"])
  async def command_work_info(self, ctx, job: str):
    """Get information about a job"""
    jobs = await self.config.JOBS()
    job = jobs.get(job)

    if not job:
      await ctx.send(embed=ErrorEmbed("That job does not exist!"))
      return
    else:
      currency = await bank.get_currency_name(ctx.guild)
      embed = discord.Embed(title=f"{job['emoji']} {job['name']}", description=job['description'])

      for tier in job['tiers']:
        embed.add_field(
          name=tier['name'],
          value=f"Rate: {humanize_number(tier['rate'])} {currency}/hour\n"
                f"{tier['min_hours']}-{tier['max_hours']} hours/shift",
          inline=False
        )

      await ctx.send(embed=embed)

  @command_work.command(name="status")
  async def command_work_status(self, ctx):
    """Check your current job status"""
    job = await self.config.member(ctx.author).job()
    tier = await self.config.member(ctx.author).job_tier()
    times_worked = await self.config.member(ctx.author).job_times_worked()
    global_times_worked = await self.config.member(ctx.author).job_global_times_worked()

    if job:
      jobs = await self.config.JOBS()
      job = jobs.get(job)
      tier = job['tiers'][tier]
      next_tier = job['tiers'][tier + 1] if tier + 1 < len(job['tiers']) else None
      currency = await bank.get_currency_name(ctx.guild)

      embed = discord.Embed(title=f"{job['emoji']} {job['name']} - {tier['name']}")
      embed.add_field(
        name="Rate",
        value=f"{humanize_number(tier['rate'])} {currency}/hour",
        inline=True
      )

      if next_tier:
        embed.add_field(
          name="Promotion",
          value=f"Promotion in {tier['times_worked'] - times_worked} shifts",
          inline=True
        )
      else:
        embed.add_field(
          name="Promotion",
          value="You are at the highest tier!",
          inline=True
        )

      embed.add_field(
        name="Times Worked",
        value=f"Current job: {times_worked} times\n"
              f"Global: {global_times_worked} times",
        inline=True
      )

      await ctx.send(embed=embed)
    else:
      await ctx.send(embed=ErrorEmbed("You do not have a job!"))

  @command_work.command(name="apply")
  async def command_work_apply(self, ctx, job: str):
    """Apply for a job"""
    jobs = await self.config.JOBS()
    job = jobs.get(job)

    if not job:
      await ctx.send(embed=ErrorEmbed("That job does not exist!"))
      return

    current_job = await self.config.member(ctx.author).job()
    if current_job:
      await ctx.send(embed=ErrorEmbed("You already have a job!"))
      return

    job_cooldown = await self.config.JOB_APPLY_COOLDOWN()
    last_quit = await self.config.member(ctx.author).job_last_quit()
    cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())

    if cur_time < last_quit + job_cooldown:
      relative_time = discord.utils.format_dt(
        datetime.now(timezone.utc) + timedelta(seconds=last_quit + job_cooldown - cur_time), "R"
      )
      await ctx.send(f"You are still on cooldown for applying to a job! You will be able to apply for another job {relative_time}")
      return

    if job['min_times_worked'] > await self.config.member(ctx.author).job_global_times_worked():
      await ctx.send(embed=ErrorEmbed("You do not meet the requirements for this job!"))
      return

    currency = await bank.get_currency_name(ctx.guild)

    await self.config.member(ctx.author).job.set(job)
    await self.config.member(ctx.author).job_tier.set(0)
    await self.config.member(ctx.author).job_times_worked.set(0)

    await ctx.send(embed=discord.Embed(
        title="Job Applied",
        description=f"You have successfully applied for the job of {job['name']}!\n"
          f"Your hourly rate is now {humanize_number(job['tiers'][0]['rate'])} {currency}/hour",
    ))

  @command_work.command(name="quit")
  async def command_work_quit(self, ctx):
    """Quit your current job. Warning, you will not be able to apply for a job for a while!"""
    job = await self.config.member(ctx.author).job()
    if not job:
      await ctx.send(embed=ErrorEmbed("You do not have a job!"))
      return

    job_cooldown = await self.config.JOB_APPLY_COOLDOWN()
    cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())

    await self.config.member(ctx.author).job_last_quit.set(cur_time)
    await self.config.member(ctx.author).job.set(None)
    await self.config.member(ctx.author).job_tier.set(0)
    await self.config.member(ctx.author).job_times_worked.set(0)

    await ctx.send("Are you sure you want to quit your job? Type `yes` in the next 10 seconds to confirm.")

    try:
      await self.bot.wait_for("message", check=lambda m: m.author == ctx.author and m.content.lower() == "yes", timeout=10)
    except TimeoutError:
      return

    await ctx.send(embed=discord.Embed(
        title="Job Quit",
        description=f"You have successfully quit your job at {job['name']}!\n"
          f"You will be able to apply for a job again {discord.utils.format_dt(datetime.now(timezone.utc) + timedelta(seconds=job_cooldown), 'R')}",
    ))

  @command_work.command(name="fire", aliases=["sack", "dismiss"])
  @commands.admin()
  async def command_work_fire(self, ctx, member: discord.Member):
    """Fire a member from their job"""

  @command_work.command(name="cooldown")
  async def command_work_cooldown(self, ctx):
    """Check how long until you can work again"""
    job = await self.config.member(ctx.author).job()
    if not job:
      await ctx.send(embed=ErrorEmbed("You do not have a job!"))
      return

    job_cooldown = await self.config.JOB_COOLDOWN()
    last_worked = await self.config.member(ctx.author).job_last_worked()
    cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())

    if cur_time < last_worked + job_cooldown:
      relative_time = discord.utils.format_dt(
        datetime.now(timezone.utc) + timedelta(seconds=last_worked + job_cooldown - cur_time), "R"
      )
      await ctx.send(f"You will be able to work again {relative_time}.")
    else:
      await ctx.send("You are not on cooldown and can work now!")

  @command_work.command(name="shift", aliases=["work"])
  async def command_work_shift(self, ctx):
    """Work a shift"""
    job = await self.config.member(ctx.author).job()
    if not job:
      await ctx.send(embed=ErrorEmbed("You do not have a job!"))
      return

    job = await self.config.JOBS.get(job)
    tier_int = await self.config.member(ctx.author).job_tier()
    tier = job['tiers'][tier_int]

    job_cooldown = await self.config.JOB_COOLDOWN()
    last_worked = await self.config.member(ctx.author).job_last_worked()
    cur_time = calendar.timegm(ctx.message.created_at.utctimetuple())

    if cur_time < last_worked + job_cooldown:
      relative_time = discord.utils.format_dt(
        datetime.now(timezone.utc) + timedelta(seconds=last_worked + job_cooldown - cur_time), "R"
      )
      await ctx.send(f"You are still on cooldown for working! You will be able to work again {relative_time}")
      return

    currency = await bank.get_currency_name(ctx.guild)

    hours = randint(tier['min_hours'], tier['max_hours'])
    rate = tier['rate']
    earnings = hours * rate

    await self.config.member(ctx.author).job_last_worked.set(cur_time)
    await self.config.member(ctx.author).job_times_worked.set(await self.config.member(ctx.author).job_times_worked() + 1)
    await self.config.member(ctx.author).job_global_times_worked.set(await self.config.member(ctx.author).job_global_times_worked() + 1)

    message = f"You have worked a {hours} hour shift at {job['name']} and earned {humanize_number(earnings)} {currency}!"

    next_tier = job['tiers'][tier_int + 1] if tier_int + 1 < len(job['tiers']) else None

    if next_tier and await self.config.member(ctx.author).job_times_worked() >= next_tier['times_worked']:
      await self.config.member(ctx.author).job_tier.set(await self.config.member(ctx.author).job_tier() + 1)
      message += f"\nYou have been promoted to {next_tier['name']}! Your new rate is {humanize_number(next_tier['rate'])} {currency}/hour"

    bank.deposit_credits(ctx.author, earnings)

    await ctx.send(message)